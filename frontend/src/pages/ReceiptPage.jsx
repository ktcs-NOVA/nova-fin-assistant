// U-06 영수증 자동 정리 (영수증 등록)
// 왼쪽: 사진 고르기 (샘플 11장 또는 내 사진) → "영수증 인식"
// 오른쪽: 인식 결과를 수정 가능한 폼에 채움 → "지출 건 초안" 으로 다음 단계(지출 건 생성)에 넘길 값 확인
//
// 목업 모드: 샘플 사진은 experiments/receipt-ocr 1차 테스트에서 실제로 받은 결과를 보여줍니다.
// 백엔드 연결 모드: 사진을 base64 로 POST /api/receipt 에 보내 실제로 인식합니다.
//
// "청구 검증으로 보내기": 초안을 U-04 청구 검증 폼의 항목 1건으로 넘깁니다 (App.jsx 의 sendToVerify).
// PM 엔진은 초안 이름(purpose, business_type, total_amount)을 그대로 읽고, 영수증 건은 payment 를 "법인카드" 로 넣으면
// 심야·제한업종 규칙까지 검사합니다 (docs/U-04_청구검증_입력필드.md 4절).

import { useState } from 'react'
import { recognizeReceipt, PURPOSES, USE_MOCK } from '../api/client.js'
import receiptsData from '../mocks/receipts.json'
import CameraCapture from '../components/CameraCapture.jsx'
import Icon from '../components/Icons.jsx'

const SAMPLES = receiptsData.samples
const imageUrl = (file) => `${import.meta.env.BASE_URL}receipts/${file}`

// 폼에 보여줄 칸 (순서대로). key 는 API 응답 필드명.
const FIELDS = [
  { key: 'merchant', label: '가맹점', required: true },
  { key: 'business_type', label: '업종' },
  { key: 'date', label: '날짜', required: true, placeholder: 'YYYY-MM-DD' },
  { key: 'time', label: '시각', placeholder: 'HH:MM' },
  { key: 'total_amount', label: '합계 금액', required: true, type: 'number' },
  { key: 'card_last4', label: '카드 뒷 4자리' },
  { key: 'approval_no', label: '승인번호' },
]

const CONFIDENCE = {
  high: { label: '신뢰도 높음', cls: 'good' },
  medium: { label: '신뢰도 보통 · 확인 필요', cls: 'warn' },
  low: { label: '신뢰도 낮음 · 직접 확인', cls: 'bad' },
}

// 파일 → base64 (data: 접두어 제거)
function readAsBase64(blob) {
  return new Promise((resolve, reject) => {
    const r = new FileReader()
    r.onload = () => resolve(String(r.result).split(',')[1])
    r.onerror = () => reject(new Error('사진 파일을 읽지 못했습니다.'))
    r.readAsDataURL(blob)
  })
}

export default function ReceiptPage({ onSendToVerify }) {
  const [photo, setPhoto] = useState(null)      // { file, url, blob?, sample: bool }
  const [form, setForm] = useState(null)        // 인식 결과 (수정 가능)
  const [raw, setRaw] = useState(null)          // 인식 원본 (수정 전 비교용)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [draft, setDraft] = useState(null)      // 지출 건 초안
  const [camera, setCamera] = useState(false)   // 촬영 뷰파인더 열림
  const [showSamples, setShowSamples] = useState(false)  // 샘플 영수증 목록 펼침 (시연용)

  function pickSample(s) {
    setPhoto({ file: s.file, url: imageUrl(s.file), sample: true, label: s.label })
    setForm(null); setRaw(null); setDraft(null); setError('')
  }

  function pickOwn(e) {
    const f = e.target.files?.[0]
    if (!f) return
    setPhoto({ file: f.name, url: URL.createObjectURL(f), blob: f, sample: false, label: f.name })
    setForm(null); setRaw(null); setDraft(null); setError('')
  }

  // 뷰파인더에서 찍은 사진은 "내 사진 올리기" 와 똑같이 취급
  function pickShot(blob, filename) {
    setPhoto({ file: filename, url: URL.createObjectURL(blob), blob, sample: false, label: '카메라 촬영' })
    setForm(null); setRaw(null); setDraft(null); setError('')
    setCamera(false)
  }

  async function recognize() {
    if (!photo) return
    setLoading(true); setError(''); setDraft(null)
    try {
      let base64 = null
      let mediaType = null
      if (!USE_MOCK) {
        // 샘플은 public/ 에서 받아오고, 내 사진은 선택한 파일 그대로
        const blob = photo.blob ?? (await (await fetch(photo.url)).blob())
        base64 = await readAsBase64(blob)
        mediaType = blob.type || 'image/jpeg'
      }
      const r = await recognizeReceipt({ filename: photo.file, mediaType, base64 })
      setRaw(r)
      setForm({
        ...r,
        purpose: r.purpose_candidates?.[0] ?? '',
        items: r.items ?? [],
      })
    } catch (e) {
      setError(e.message)
      setForm(null)
    } finally {
      setLoading(false)
    }
  }

  function edit(key, value) {
    setForm((f) => ({ ...f, [key]: value }))
    setDraft(null)
  }

  function makeDraft() {
    const missing = FIELDS.filter((f) => f.required && !String(form[f.key] ?? '').trim()).map((f) => f.label)
    if (missing.length) {
      setError(`필수 값이 비어 있습니다: ${missing.join(', ')}`)
      return
    }
    setError('')
    setDraft({
      merchant: form.merchant,
      business_type: form.business_type || null,
      date: form.date,
      time: form.time || null,
      amount: Number(form.total_amount),
      purpose: form.purpose,
      card_last4: form.card_last4 || null,
      approval_no: form.approval_no || null,
      receipt_file: photo.file,
      edited_fields: FIELDS.filter((f) => String(raw[f.key] ?? '') !== String(form[f.key] ?? '')).map((f) => f.key),
    })
  }

  // 초안 → 청구 검증 폼 항목. 이름은 PM 엔진이 읽는 쪽(field, merchant_type, amount)으로 맞춰 보냄.
  function sendToVerify() {
    onSendToVerify?.({
      trip_type: '법인카드',
      items: [{
        field: draft.purpose,
        amount: String(draft.amount),
        date: draft.date,
        time: draft.time ?? '',
        merchant: draft.merchant,
        merchant_type: draft.business_type ?? '',
        payment: '법인카드',
        note: '',
        receipt_file: draft.receipt_file,
      }],
    })
  }

  const conf = form ? CONFIDENCE[form.confidence] ?? CONFIDENCE.medium : null
  // 용도 드롭다운: AI 후보를 앞에, 나머지를 뒤에
  const purposeOptions = form
    ? [...(form.purpose_candidates ?? []), ...PURPOSES.filter((p) => !(form.purpose_candidates ?? []).includes(p))]
    : PURPOSES

  return (
    <section>
      <div className="page-title">
        <h1>영수증 등록</h1>
        <span className="desc">영수증 사진에서 가맹점·금액·일시·용도를 자동으로 읽어 지출 건 초안을 만듭니다.</span>
      </div>

      <div className="receipt-layout">
        {/* ---------- 왼쪽: 사진 ---------- */}
        <div className="card">
          <h2>1. 영수증 사진</h2>

          {/* 사진이 아직 없을 때: 찍기 / 업로드 두 갈래 */}
          {!photo && !camera && (
            <>
              <p className="hint">영수증을 어떻게 가져올까요?</p>
              <div className="start-row">
                <button type="button" className="start-btn" onClick={() => setCamera(true)}>
                  <Icon name="camera" size={34} />
                  <b>영수증 사진 찍기</b>
                  <small>카메라로 바로 찍어요</small>
                </button>
                <label className="start-btn">
                  <input type="file" accept="image/jpeg,image/png,image/webp" onChange={pickOwn} />
                  <Icon name="upload" size={34} />
                  <b>영수증 업로드</b>
                  <small>jpg · png · webp</small>
                </label>
              </div>
              <button type="button" className="link-btn sample-toggle" onClick={() => setShowSamples((v) => !v)}>
                {showSamples ? '샘플 영수증 닫기' : '샘플 영수증으로 해보기'}
              </button>
              {showSamples && (
                <>
                  {USE_MOCK && <p className="hint">목업 모드에서는 샘플 11장만 인식됩니다 (1차 테스트에서 받은 실제 결과).</p>}
                  <div className="thumb-grid" role="list">
                    {SAMPLES.map((s) => (
                      <button key={s.file} type="button" role="listitem" className="thumb" onClick={() => pickSample(s)} title={s.label}>
                        <img src={imageUrl(s.file)} alt={s.label} loading="lazy" />
                        <span>{s.label}</span>
                      </button>
                    ))}
                  </div>
                </>
              )}
            </>
          )}

          {camera && <CameraCapture onCapture={pickShot} onClose={() => setCamera(false)} />}

          {/* 사진을 고르면(찍기·업로드·샘플) 그 영수증이 보임 */}
          {photo && !camera && (
            <>
              <div className="preview">
                <img className="preview-img" src={photo.url} alt={photo.label} />
                <div className="preview-name">{photo.label}</div>
              </div>
              <div className="btn-row between">
                <button type="button" className="btn" onClick={() => { setPhoto(null); setForm(null); setRaw(null); setDraft(null); setError('') }}>
                  다시 고르기
                </button>
                <button className="btn primary" onClick={recognize} disabled={loading}>
                  {loading ? '인식 중… (5초 안팎)' : '영수증 인식'}
                </button>
              </div>
            </>
          )}
        </div>

        {/* ---------- 오른쪽: 결과 ---------- */}
        <div className="card">
          <h2>2. 인식 결과</h2>
          {error && <div className="error">{error}</div>}

          {!form ? (
            <div className="empty">사진을 고르고 "영수증 인식"을 누르면 읽어낸 값이 여기에 채워집니다.<br />값은 저장 전에 직접 고칠 수 있습니다.</div>
          ) : (
            <>
              <div className="conf-row">
                <span className={`badge ${conf.cls}`}>{conf.label}</span>
                {form.purpose_candidates?.length > 0 && (
                  <span className="hint">용도 후보: {form.purpose_candidates.join(' › ')}</span>
                )}
              </div>

              <div className="form-grid">
                {FIELDS.map((f) => {
                  const v = form[f.key]
                  const missing = v === null || v === undefined || v === ''
                  return (
                    <label key={f.key} className={`field ${missing ? 'missing' : ''}`}>
                      <span className="field-label">
                        {f.label}{f.required && ' *'}
                        {missing && <em>읽지 못함</em>}
                      </span>
                      <input
                        type={f.type ?? 'text'}
                        value={v ?? ''}
                        placeholder={f.placeholder ?? (missing ? '직접 입력' : '')}
                        onChange={(e) => edit(f.key, e.target.value)}
                      />
                    </label>
                  )
                })}

                <label className="field">
                  <span className="field-label">용도 *</span>
                  <select value={form.purpose} onChange={(e) => edit('purpose', e.target.value)}>
                    {purposeOptions.map((p) => (
                      <option key={p} value={p}>
                        {p}{form.purpose_candidates?.includes(p) ? ' (AI 추천)' : ''}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              {form.items.length > 0 && (
                <>
                  <div className="section-title">품목 ({form.items.length})</div>
                  <table className="table items-table">
                    <tbody>
                      {form.items.map((it, i) => (
                        <tr key={i}>
                          <td>{it.name}</td>
                          <td className="num">{it.amount != null ? it.amount.toLocaleString('ko-KR') + '원' : '-'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </>
              )}

              {form.notes && (
                <>
                  <div className="section-title">AI 메모 (사람이 확인할 부분)</div>
                  <p className="notes-box">{form.notes}</p>
                </>
              )}

              <div className="btn-row">
                <button className="btn primary" onClick={makeDraft}>지출 건 초안 만들기</button>
              </div>

              {draft && (
                <div className="card preview-card draft-card">
                  <div className="preview-head">
                    <strong>지출 건 초안</strong>
                    <span className="hint">다음 단계 "지출 건 생성" 으로 넘어갈 값</span>
                  </div>
                  <dl className="info-grid">
                    <dt>가맹점</dt><dd>{draft.merchant}{draft.business_type ? ` (${draft.business_type})` : ''}</dd>
                    <dt>금액</dt><dd>{draft.amount.toLocaleString('ko-KR')}원</dd>
                    <dt>일시</dt><dd>{draft.date}{draft.time ? ` ${draft.time}` : ''}</dd>
                    <dt>용도</dt><dd>{draft.purpose}</dd>
                    <dt>카드</dt><dd>{draft.card_last4 ? `**** ${draft.card_last4}` : '미확인'}</dd>
                    <dt>승인번호</dt><dd>{draft.approval_no ?? '-'}</dd>
                  </dl>
                  <p className="hint" style={{ marginTop: 8 }}>
                    {draft.edited_fields.length
                      ? `사용자가 고친 칸: ${draft.edited_fields.join(', ')}`
                      : '인식값을 그대로 사용 (수정 없음)'}
                  </p>
                  <div className="btn-row">
                    <button type="button" className="btn primary" onClick={sendToVerify}>
                      청구 검증으로 보내기 →
                    </button>
                  </div>
                  <p className="hint">법인카드 결제 건으로 청구 검증 폼에 채워집니다. 필요하면 그 화면에서 항목을 더 넣고 "검증하기"를 누르세요.</p>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </section>
  )
}
