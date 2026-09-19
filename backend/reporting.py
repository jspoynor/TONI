"""Deterministic draft validation; consumes structured evidence, never raw OCR text."""
from __future__ import annotations
from datetime import date, datetime, timezone
from typing import Literal
import hashlib
import json
from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictFloat, StrictStr, model_validator

FieldName = Literal['revenue','cash_on_hand','arr','management_context','risks','help_requested']
NAMES = ('revenue','cash_on_hand','arr','management_context','risks','help_requested')
FINANCIAL = {'revenue','cash_on_hand','arr'}

class Model(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)

class Source(Model):
    kind: Literal['document','company_answer']
    file: str | None = None
    page: int | None = Field(default=None, ge=1)
    message_id: str | None = None
    quote: str = Field(min_length=1)
    uncertain: bool = False

    @model_validator(mode='after')
    def reference(self):
        if not self.quote.strip(): raise ValueError('Evidence quote must not be blank')
        if self.kind == 'document' and (not self.file or self.page is None):
            raise ValueError('Document evidence requires file and page')
        if self.kind == 'company_answer' and not self.message_id:
            raise ValueError('Company evidence requires message_id')
        return self

class Request(Model):
    request_id: str = Field(min_length=1)
    company_id: str = Field(min_length=1)
    frequency: Literal['monthly','quarterly']
    period_start: date
    period_end: date
    due_date: date
    currency: str = Field(pattern=r'^[A-Z]{3}$')
    required_fields: list[FieldName] = Field(default_factory=lambda:list(NAMES))
    arr_applicable: bool | None = None
    max_questions: int = Field(default=3, ge=1, le=3)

    @model_validator(mode='after')
    def dates(self):
        if self.period_end < self.period_start: raise ValueError('Period end precedes start')
        if self.due_date < self.period_end: raise ValueError('Due date precedes period end')
        if len(set(self.required_fields)) != len(self.required_fields): raise ValueError('Duplicate required fields')
        return self

class Candidate(Model):
    id: str = Field(min_length=1)
    company_id: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    value: StrictInt | StrictFloat | StrictStr
    currency: str | None = None
    unit: Literal['base_units','thousands','millions'] | None = None
    period_start: date | None = None
    period_end: date | None = None
    as_of_date: date | None = None
    definition: str | None = None
    source: Source

class FieldEvidence(Model):
    candidates: list[Candidate] = Field(default_factory=list)
    selected_id: str | None = None
    resolution: Source | None = None

    @model_validator(mode='after')
    def selection(self):
        ids = [c.id for c in self.candidates]
        if len(ids) != len(set(ids)): raise ValueError('Candidate IDs must be unique within a field')
        if self.selected_id is not None:
            if self.selected_id not in ids: raise ValueError('Unknown selected candidate')
            if not self.resolution or self.resolution.kind != 'company_answer':
                raise ValueError('Choosing between candidates requires a company-answer reference')
        elif self.resolution is not None: raise ValueError('Resolution requires selected_id')
        return self

class Draft(Model):
    request: Request
    fields: dict[FieldName, FieldEvidence] = Field(default_factory=dict)

    @model_validator(mode='after')
    def scope(self):
        for evidence in self.fields.values():
            for c in evidence.candidates:
                if (c.company_id,c.request_id)!=(self.request.company_id,self.request.request_id):
                    raise ValueError('Evidence belongs to another company or reporting request')
        return self

QUESTIONS = {
 'revenue':'Please provide revenue for {start} through {end} in {currency}.',
 'cash_on_hand':'What was your cash balance in {currency} as of {end}?',
 'arr':'What was your ARR in {currency} as of {end}, and how do you define it? If not applicable, please say so.',
 'management_context':'What changed during this reporting period, and what explains those changes?',
 'risks':'What material risks are you facing, and what actions are you taking? You may explicitly report none.',
 'help_requested':'What specific help would you like from your investors? You may explicitly report none.'}

def signature(c: Candidate):
    return (c.value,c.currency,c.unit,c.period_start,c.period_end,c.as_of_date,c.definition)

def candidate_issues(name: str, c: Candidate, req: Request):
    issues=[]
    if c.source.uncertain: issues.append('source_uncertain')
    if name in FINANCIAL:
        if isinstance(c.value, bool) or not isinstance(c.value,(int,float)): issues.append('amount_not_numeric')
        if c.currency != req.currency: issues.append('currency_missing_or_different')
        if c.unit != 'base_units': issues.append('units_missing_or_not_normalized')
        if name=='revenue' and (c.period_start,c.period_end)!=(req.period_start,req.period_end):
            issues.append('reporting_period_missing_or_wrong')
        if name!='revenue' and c.as_of_date != req.period_end: issues.append('as_of_date_missing_or_wrong')
        if name=='arr' and not (c.definition and c.definition.strip()): issues.append('arr_definition_missing')
        if name=='arr' and isinstance(c.value,(int,float)) and c.value<0: issues.append('arr_negative')
    else:
        if not isinstance(c.value,str) or not c.value.strip(): issues.append('narrative_missing_or_invalid')
        # Narrative periods are explicit in the new contract, unlike the initial sample payload.
        if (c.period_start,c.period_end)!=(req.period_start,req.period_end): issues.append('reporting_period_missing_or_wrong')
    return issues

def validate(draft: Draft | dict) -> dict:
    # Revalidate even existing model objects to reject invalid post-construction mutations.
    draft=Draft.model_validate(draft.model_dump(mode='json') if isinstance(draft,Draft) else draft)
    req=draft.request;result={};pending=[]
    for name in NAMES:
        evidence=draft.fields.get(name,FieldEvidence());cs=evidence.candidates
        required=name in req.required_fields
        value=None;source=None;issues=[];status='missing'
        if name=='arr' and req.arr_applicable is False and not cs:
            status='not_applicable'
        elif not cs:
            if required: issues=['missing']
        else:
            distinct={signature(c) for c in cs}
            if len(distinct)>1 and evidence.selected_id is None:
                issues=['conflicting_candidates'];status='conflicting'
            else:
                c=next(c for c in cs if c.id==evidence.selected_id) if evidence.selected_id else cs[0]
                issues=candidate_issues(name,c,req)
                # Identical values cannot hide uncertainty in any unselected evidence.
                if evidence.selected_id is None and any(x.source.uncertain for x in cs) and 'source_uncertain' not in issues:
                    issues.append('source_uncertain')
                if name=='arr' and req.arr_applicable is False: issues.append('arr_applicability_conflict')
                status='needs_clarification' if issues else 'ready'
                if not issues: value=c.value;source=c.source.model_dump(mode='json')
        result[name]={'required':required,'status':status,'value':value,'issues':issues,'source':source,
                      'candidates':[c.model_dump(mode='json') for c in cs],
                      'resolution':evidence.resolution.model_dump(mode='json') if evidence.resolution else None,
                      'confirmed':False}
        # Optional blank fields don't block. Optional provided but invalid data does block.
        if issues:
            if 'conflicting_candidates' in issues:
                question=f'We found conflicting values for {name.replace("_"," ")}. Which is correct? Please confirm currency, units and reporting date where relevant.';priority=0
            elif issues!=['missing']:
                question=f'Please clarify {name.replace("_"," ")}: '+', '.join(x.replace('_',' ') for x in issues)+'.';priority=1
            else:
                question=QUESTIONS[name].format(start=req.period_start,end=req.period_end,currency=req.currency)
                priority=2 if name in FINANCIAL else 3
            pending.append({'field':name,'priority':priority,'question':question})
    pending.sort(key=lambda x:x['priority'])
    return {'schema_version':'1.0','request':req.model_dump(mode='json'),'status':'needs_information' if pending else 'ready_for_review',
            'fields':result,'questions':pending[:req.max_questions],'remaining_question_count':max(0,len(pending)-req.max_questions),
            'ready_for_review':not pending,'confirmed':False}

def review_hash(draft: Draft | dict) -> str:
    draft=Draft.model_validate(draft.model_dump(mode='json') if isinstance(draft,Draft) else draft)
    return hashlib.sha256(json.dumps(draft.model_dump(mode='json'),sort_keys=True,separators=(',',':')).encode()).hexdigest()

def submit(draft: Draft | dict, *, reviewed_hash: str, confirmed_by: str, company_confirmed: bool, version: int) -> str:
    """Return a detached immutable JSON string. Caller persists it as a new version."""
    if company_confirmed is not True or not confirmed_by.strip(): raise ValueError('Explicit identified company confirmation required')
    if type(version) is not int or version<1: raise ValueError('Positive report version required')
    result=validate(draft)
    if not result['ready_for_review']: raise ValueError('Resolve outstanding issues before submission')
    if review_hash(draft)!=reviewed_hash: raise ValueError('Draft changed after review; review again')
    result.update(status='submitted',confirmed=True,confirmed_by=confirmed_by,version=version,
                  confirmed_at=datetime.now(timezone.utc).isoformat(),reviewed_hash=reviewed_hash)
    for field in result['fields'].values():
        field['confirmed']=field['status'] in ('ready','not_applicable')
    return json.dumps(result,indent=2)

if __name__=='__main__':
    import argparse
    from pathlib import Path
    parser=argparse.ArgumentParser();parser.add_argument('draft',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args();res=json.dumps(validate(json.loads(args.draft.read_text())),indent=2)
    if args.output: args.output.write_text(res)
    else: print(res)
