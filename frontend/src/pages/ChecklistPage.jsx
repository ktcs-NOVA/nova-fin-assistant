// 내 체크리스트 화면 (U-02)
// 규정 Q&A의 업무 절차 안내에서 저장한 업무를 모아 보고, 끝낸 항목을 체크합니다.
// 데이터 모양은 docs/API.md 3-7 와 같습니다.

import { useEffect, useState } from 'react'
import {
  VERDICT,
  deleteChecklist,
  getChecklists,
  updateChecklistItem,
} from '../api/client.js'
import SourceList from '../components/SourceList.jsx'

const SECTIONS = [
  { kind: 'document', label: '필요 서류' },
  { kind: 'step', label: '작성 순서' },
]

const formatDate = (value) =>
  new Intl.DateTimeFormat('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' }).format(new Date(value))

function Fact({ label, fact }) {
  if (!fact) return null
  return (
    <div className="checklist-fact">
      <dt>
        {label}
        {fact.check && <span className="badge warn">{VERDICT.CHECK}</span>}
      </dt>
      <dd>
        {fact.text}
        {fact.basis && <span className="basis">근거 · {fact.basis}</span>}
      </dd>
    </div>
  )
}

function ChecklistCard({ checklist, defaultOpen, onToggle, onDelete }) {
  const { task, summary, deadline, approver, sources, created_at: createdAt, items } = checklist
  const doneCount = items.filter((i) => i.done).length
  const complete = items.length > 0 && doneCount === items.length
  const percent = items.length ? Math.round((doneCount / items.length) * 100) : 0

  return (
    <details className="checklist-card" open={defaultOpen}>
      <summary>
        <span className="checklist-title">
          <strong>{task}</strong>
          <span className="hint">{formatDate(createdAt)} 저장</span>
        </span>
        <span className={`badge ${complete ? 'good' : 'muted'}`}>
          {complete ? '완료' : `${doneCount}/${items.length}`}
        </span>
        <span
          className="progress"
          role="progressbar"
          aria-label={`${task} 진행률`}
          aria-valuemin="0"
          aria-valuemax="100"
          aria-valuenow={percent}
        >
          <span style={{ width: `${percent}%` }} />
        </span>
      </summary>

      <div className="checklist-body">
        {summary && <p className="answer-text">{summary}</p>}

        {SECTIONS.map(({ kind, label }) => {
          const rows = items.filter((i) => i.kind === kind)
          if (!rows.length) return null
          return (
            <section key={kind}>
              <h3>{label}</h3>
              <ul className="todo-list">
                {rows.map((item) => (
                  <li key={item.id} className={item.done ? 'done' : ''}>
                    <label>
                      <input
                        type="checkbox"
                        checked={item.done}
                        onChange={(e) => onToggle(checklist.id, item.id, e.target.checked)}
                      />
                      <span>
                        <span className="todo-title">{item.title}</span>
                        {item.detail && <span className="todo-detail">{item.detail}</span>}
                        {item.basis && <span className="basis">근거 · {item.basis}</span>}
                      </span>
                    </label>
                  </li>
                ))}
              </ul>
            </section>
          )
        })}

        <dl className="checklist-facts">
          <Fact label="제출 기한" fact={deadline} />
          <Fact label="결재자" fact={approver} />
        </dl>

        <SourceList sources={sources} />
        <p className="hint">저장한 날의 규정 기준입니다. 처리 전에 근거 조항의 개정일을 확인해 주세요.</p>

        <div className="checklist-actions">
          <button type="button" className="btn small" onClick={() => onDelete(checklist)}>
            삭제
          </button>
        </div>
      </div>
    </details>
  )
}

export default function ChecklistPage({ onNavigate }) {
  const [checklists, setChecklists] = useState(null) // null 이면 불러오는 중
  const [error, setError] = useState('')

  useEffect(() => {
    let ignore = false
    getChecklists()
      .then((data) => {
        if (!ignore) setChecklists(data)
      })
      .catch((e) => {
        if (!ignore) {
          setError(e.message)
          setChecklists([])
        }
      })
    return () => {
      ignore = true
    }
  }, [])

  function setItemDone(checklistId, itemId, done) {
    setChecklists((prev) =>
      prev.map((c) =>
        c.id !== checklistId
          ? c
          : { ...c, items: c.items.map((i) => (i.id === itemId ? { ...i, done } : i)) },
      ),
    )
  }

  async function toggle(checklistId, itemId, done) {
    setError('')
    setItemDone(checklistId, itemId, done) // 먼저 화면에 반영하고, 실패하면 되돌립니다
    try {
      await updateChecklistItem(checklistId, itemId, done)
    } catch (e) {
      setItemDone(checklistId, itemId, !done)
      setError(e.message)
    }
  }

  async function remove(checklist) {
    if (!window.confirm(`'${checklist.task}' 체크리스트를 삭제할까요? 체크한 내용도 함께 지워집니다.`)) return
    setError('')
    try {
      await deleteChecklist(checklist.id)
      setChecklists((prev) => prev.filter((c) => c.id !== checklist.id))
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <section>
      <div className="page-title">
        <h1>문서 작업</h1>
        <span className="desc">저장한 업무의 할 일을 확인하고 체크합니다.</span>
      </div>

      {error && <div className="error" role="alert">{error}</div>}

      {checklists === null && <p className="loading">체크리스트를 불러오는 중…</p>}

      {checklists?.length === 0 && !error && (
        <div className="empty">
          <p>아직 저장한 체크리스트가 없습니다.</p>
          <p className="hint">규정 Q&amp;A의 업무 절차 안내에서 필요한 업무를 저장해 보세요.</p>
          <button type="button" className="btn small primary" onClick={() => onNavigate?.('qa')}>
            규정 Q&amp;A로 가기
          </button>
        </div>
      )}

      {checklists?.length > 0 && (
        <div className="checklists">
          {checklists.map((checklist, index) => (
            <ChecklistCard
              key={checklist.id}
              checklist={checklist}
              defaultOpen={index === 0}
              onToggle={toggle}
              onDelete={remove}
            />
          ))}
        </div>
      )}
    </section>
  )
}
