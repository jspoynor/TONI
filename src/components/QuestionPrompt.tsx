import { useState } from 'react'
import type { FormEvent } from 'react'
import type { FieldAnswer, QuestionAnswer, ReportQuestion } from '../types'
import './QuestionPrompt.css'

export interface QuestionPromptProps {
  question: ReportQuestion
  /** Defaults for the fields the question doesn't otherwise constrain. */
  currency: string
  periodStart: string
  periodEnd: string
  disabled: boolean
  onSubmit: (answer: QuestionAnswer, message: string) => void
}

const DATE_LABELS: Record<string, string> = {
  period_start: 'Period start',
  period_end: 'Period end',
  as_of_date: 'As of',
}

/**
 * A small structured reply form built from one question's `answer_contract`
 * (see backend/question_bank.json) — the backend has no NLP layer, so a
 * typed answer plus a human message is all it can accept. Mount with
 * `key={question.question_id}` so a new question always gets fresh, empty
 * form state rather than carrying over the previous question's inputs.
 */
function QuestionPrompt({
  question,
  currency,
  periodStart,
  periodEnd,
  disabled,
  onSubmit,
}: QuestionPromptProps) {
  const contract = question.answer_contract
  const defaultDate = (key: string) =>
    key === 'period_start' ? periodStart : periodEnd

  const [value, setValue] = useState('')
  const [currencyInput, setCurrencyInput] = useState(currency)
  const [dates, setDates] = useState<Record<string, string>>(() =>
    Object.fromEntries(
      contract.dates_required.map((key) => [key, defaultDate(key)]),
    ),
  )
  const [definition, setDefinition] = useState('')
  const [notApplicable, setNotApplicable] = useState(false)
  const [message, setMessage] = useState('')

  const applyCandidate = (candidate: (typeof question.candidate_options)[number]) => {
    if (candidate.value !== null) setValue(String(candidate.value))
    if (candidate.currency) setCurrencyInput(candidate.currency)
    setDates((prev) => {
      const next = { ...prev }
      for (const key of contract.dates_required) {
        const candidateValue = candidate[key]
        if (candidateValue) next[key] = candidateValue
      }
      return next
    })
  }

  const canSubmit =
    !disabled &&
    message.trim().length > 0 &&
    (notApplicable ||
      ((!contract.value_required || value.trim().length > 0) &&
        (!contract.currency_required || currencyInput.trim().length > 0) &&
        contract.dates_required.every((key) => dates[key]?.trim().length > 0) &&
        (!contract.definition_required || definition.trim().length > 0)))

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    if (!canSubmit) return

    if (notApplicable) {
      onSubmit({ not_applicable: true }, message.trim())
      return
    }

    const answer: FieldAnswer = {}
    if (contract.value_required) {
      answer.value = contract.type === 'number' ? Number(value) : value
    }
    if (contract.currency_required) answer.currency = currencyInput.trim()
    if (contract.unit) answer.unit = contract.unit
    for (const key of contract.dates_required) {
      answer[key] = dates[key]
    }
    if (contract.definition_required) answer.definition = definition.trim()

    onSubmit(answer, message.trim())
  }

  return (
    <form className="question-prompt" onSubmit={handleSubmit}>
      {question.candidate_options.length > 0 && (
        <div className="question-prompt-candidates">
          {question.candidate_options.map((candidate) => (
            <button
              type="button"
              key={candidate.candidate_id}
              className="question-prompt-candidate-chip"
              disabled={disabled}
              onClick={() => applyCandidate(candidate)}
            >
              Use: {candidate.value ?? '—'} {candidate.currency ?? ''}
              {candidate.as_of_date ? ` as of ${candidate.as_of_date}` : ''}
            </button>
          ))}
        </div>
      )}

      {contract.allow_explicit_not_applicable && (
        <label className="question-prompt-checkbox">
          <input
            type="checkbox"
            checked={notApplicable}
            disabled={disabled}
            onChange={(event) => setNotApplicable(event.target.checked)}
          />
          Not applicable to this business
        </label>
      )}

      {!notApplicable && (
        <div className="question-prompt-fields">
          {contract.value_required && (
            <label className="question-prompt-field">
              <span>{contract.type === 'number' ? 'Amount' : 'Answer'}</span>
              {contract.type === 'number' ? (
                <input
                  type="number"
                  step="any"
                  value={value}
                  disabled={disabled}
                  onChange={(event) => setValue(event.target.value)}
                />
              ) : (
                <textarea
                  value={value}
                  disabled={disabled}
                  onChange={(event) => setValue(event.target.value)}
                  rows={2}
                />
              )}
            </label>
          )}

          {contract.currency_required && (
            <label className="question-prompt-field question-prompt-field--narrow">
              <span>Currency</span>
              <input
                type="text"
                value={currencyInput}
                disabled={disabled}
                onChange={(event) => setCurrencyInput(event.target.value)}
              />
            </label>
          )}

          {contract.dates_required.map((key) => (
            <label
              key={key}
              className="question-prompt-field question-prompt-field--narrow"
            >
              <span>{DATE_LABELS[key] ?? key}</span>
              <input
                type="date"
                value={dates[key] ?? ''}
                disabled={disabled}
                onChange={(event) =>
                  setDates((prev) => ({ ...prev, [key]: event.target.value }))
                }
              />
            </label>
          ))}

          {contract.definition_required && (
            <label className="question-prompt-field">
              <span>Definition</span>
              <textarea
                value={definition}
                disabled={disabled}
                onChange={(event) => setDefinition(event.target.value)}
                rows={2}
              />
            </label>
          )}
        </div>
      )}

      <label className="question-prompt-field">
        <span>Your message</span>
        <textarea
          value={message}
          disabled={disabled}
          onChange={(event) => setMessage(event.target.value)}
          placeholder="Explain your answer in your own words…"
          rows={2}
        />
      </label>

      <button type="submit" className="question-prompt-submit" disabled={!canSubmit}>
        Send answer
      </button>
    </form>
  )
}

export default QuestionPrompt
