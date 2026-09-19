import unittest,json
from copy import deepcopy
from pathlib import Path
from pydantic import ValidationError
from reporting import Draft,validate,review_hash,submit
P=Path(__file__).parent/'examples'
def load(name):return json.loads((P/f'{name}_input.json').read_text())
class RulesTests(unittest.TestCase):
 def test_complete_ready_but_unconfirmed(self):
  r=validate(load('complete'));self.assertTrue(r['ready_for_review']);self.assertFalse(r['confirmed']);self.assertEqual(r['questions'],[])
 def test_missing_and_three_question_limit(self):
  r=validate(load('missing'));self.assertEqual([q['field'] for q in r['questions']],['cash_on_hand','arr','management_context']);self.assertEqual(r['remaining_question_count'],2);self.assertIsNone(r['fields']['cash_on_hand']['value'])
 def test_conflict_preserves_both(self):
  r=validate(load('conflict'));f=r['fields']['cash_on_hand'];self.assertEqual(f['status'],'conflicting');self.assertIsNone(f['value']);self.assertEqual([x['value'] for x in f['candidates']],[420000,450000])
 def test_wrong_dates_block(self):
  r=validate(load('wrong_period'));self.assertIn('reporting_period_missing_or_wrong',r['fields']['revenue']['issues']);self.assertIsNone(r['fields']['cash_on_hand']['value'])
 def test_ambiguous_units_block(self):
  d=load('complete');d['fields']['revenue']['candidates'][0]['unit']='thousands';self.assertFalse(validate(d)['ready_for_review'])
 def test_wrong_currency_block(self):
  d=load('complete');d['fields']['cash_on_hand']['candidates'][0]['currency']='EUR';self.assertIsNone(validate(d)['fields']['cash_on_hand']['value'])
 def test_zero_is_valid_not_missing(self):
  d=load('complete');d['fields']['revenue']['candidates'][0]['value']=0;self.assertTrue(validate(d)['ready_for_review'])
 def test_no_cross_company_or_request(self):
  for key in ['company_id','request_id']:
   d=load('complete');d['fields']['revenue']['candidates'][0][key]='other'
   with self.assertRaises(ValidationError):validate(d)
 def test_no_missing_source(self):
  d=load('complete');d['fields']['revenue']['candidates'][0]['source']['page']=None
  with self.assertRaises(ValidationError):validate(d)
 def test_uncertain_ocr_blocks(self):
  d=load('complete');d['fields']['revenue']['candidates'][0]['source']['uncertain']=True;self.assertIn('source_uncertain',validate(d)['fields']['revenue']['issues'])
 def test_explicit_none_is_valid_blank_not_valid(self):
  d=load('complete');c=d['fields']['risks']['candidates'][0];c['value']='No material risks reported.';self.assertTrue(validate(d)['ready_for_review']);c['value']='  ';self.assertFalse(validate(d)['ready_for_review'])
 def test_arr_not_applicable(self):
  d=load('complete');d['request']['arr_applicable']=False;d['fields']['arr']={'candidates':[]};self.assertEqual(validate(d)['fields']['arr']['status'],'not_applicable');self.assertTrue(validate(d)['ready_for_review'])
 def test_arr_definition_required(self):
  d=load('complete');d['fields']['arr']['candidates'][0]['definition']=None;self.assertFalse(validate(d)['ready_for_review'])
 def test_resolution_requires_company_evidence(self):
  d=load('conflict');d['fields']['cash_on_hand']['selected_id']='cash_on_hand-document'
  with self.assertRaises(ValidationError):validate(d)
 def test_resolved_retains_candidates(self):
  r=validate(load('resolved'));self.assertTrue(r['ready_for_review']);self.assertEqual(len(r['fields']['cash_on_hand']['candidates']),2)
 def test_unresolved_cannot_submit(self):
  d=load('missing')
  with self.assertRaises(ValueError):submit(d,reviewed_hash=review_hash(d),confirmed_by='finance',company_confirmed=True,version=1)
 def test_confirmation_and_stale_hash(self):
  d=load('complete');h=review_hash(d)
  with self.assertRaises(ValueError):submit(d,reviewed_hash=h,confirmed_by='finance',company_confirmed=False,version=1)
  d['fields']['revenue']['candidates'][0]['value']=1
  with self.assertRaises(ValueError):submit(d,reviewed_hash=h,confirmed_by='finance',company_confirmed=True,version=1)
 def test_snapshot_does_not_change_with_draft(self):
  d=load('complete');s=submit(d,reviewed_hash=review_hash(d),confirmed_by='finance',company_confirmed=True,version=1);d['fields']['revenue']['candidates'][0]['value']=1;self.assertEqual(json.loads(s)['fields']['revenue']['value'],120000)
 def test_quarterly_explicit_period(self):
  d=load('complete');d['request'].update(frequency='quarterly',period_start='2026-04-01',period_end='2026-06-30',due_date='2026-07-15')
  self.assertFalse(validate(d)['ready_for_review'])
  for f in d['fields'].values():
   for c in f['candidates']:
    if c['as_of_date']:c['as_of_date']='2026-06-30'
    else:c.update(period_start='2026-04-01',period_end='2026-06-30')
  self.assertTrue(validate(d)['ready_for_review'])
 def test_future_due_date_and_nonfinite_types(self):
  d=load('complete');d['request']['due_date']='2026-07-01'
  with self.assertRaises(ValidationError):validate(d)
  for value in [float('inf'),float('nan'),True]:
   d=load('complete');d['fields']['revenue']['candidates'][0]['value']=value
   with self.assertRaises(ValidationError):validate(d)
 def test_answered_fields_leave_question_queue(self):
  d=load('missing');complete=load('complete')
  for name in ['cash_on_hand','arr','management_context']:d['fields'][name]=complete['fields'][name]
  self.assertEqual([q['field'] for q in validate(d)['questions']],['risks','help_requested'])
 def test_optional_missing_allowed_optional_conflict_blocked(self):
  d=load('missing');d['request']['required_fields']=['revenue'];self.assertTrue(validate(d)['ready_for_review']);d['fields']['cash_on_hand']=load('conflict')['fields']['cash_on_hand'];self.assertFalse(validate(d)['ready_for_review'])
if __name__=='__main__':unittest.main()
