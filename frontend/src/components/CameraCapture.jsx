// 영수증 촬영 뷰파인더 (U-06 보조)
// 브라우저 카메라(노트북 웹캠 / 폰 후면 카메라)를 켜서 미리보기를 보여주고,
// 셔터를 누르면 그 장면을 JPEG 로 캡처해 onCapture(blob, filename) 으로 넘깁니다.
// 카메라는 https 또는 localhost 에서만 켜집니다.

import { useEffect, useRef, useState } from 'react'

// 권한·장치 오류를 사람이 읽을 문장으로
function explain(err) {
  if (!navigator.mediaDevices?.getUserMedia) {
    return '이 브라우저에서는 카메라를 쓸 수 없습니다. 카메라는 https 또는 localhost 주소에서만 켜집니다.'
  }
  switch (err?.name) {
    case 'NotAllowedError':
    case 'SecurityError':
      return '카메라 권한이 거부되었습니다. 주소창의 카메라 아이콘에서 허용한 뒤 다시 시도하거나, "내 사진 올리기"를 이용해 주세요.'
    case 'NotFoundError':
    case 'OverconstrainedError':
      return '사용할 수 있는 카메라를 찾지 못했습니다. 웹캠이 연결되어 있는지 확인해 주세요.'
    case 'NotReadableError':
      return '다른 프로그램이 카메라를 쓰고 있어 켤 수 없습니다. 화상회의 앱 등을 닫고 다시 시도해 주세요.'
    default:
      return `카메라를 켜지 못했습니다. (${err?.message ?? '알 수 없는 오류'})`
  }
}

const stamp = () => {
  const d = new Date()
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}_${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`
}

export default function CameraCapture({ onCapture, onClose }) {
  const videoRef = useRef(null)
  const streamRef = useRef(null)
  const [devices, setDevices] = useState([])      // 카메라 목록 (권한 허용 후 이름이 보임)
  const [deviceId, setDeviceId] = useState('')    // 고른 카메라
  const [error, setError] = useState('')
  const [ready, setReady] = useState(false)
  const [shot, setShot] = useState(null)          // { blob, url } 캡처한 사진

  // 카메라 켜기 (deviceId 가 바뀌면 다시 켬)
  useEffect(() => {
    let cancelled = false

    async function start() {
      setReady(false)
      setError('')
      stop()
      if (!navigator.mediaDevices?.getUserMedia) {
        setError(explain(null))
        return
      }
      const video = deviceId
        ? { deviceId: { exact: deviceId } }
        : { facingMode: { ideal: 'environment' } }   // 폰이면 후면, 노트북이면 기본 웹캠
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { ...video, width: { ideal: 1920 }, height: { ideal: 1080 } },
          audio: false,
        })
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop())
          return
        }
        streamRef.current = stream
        if (videoRef.current) {
          videoRef.current.srcObject = stream
          await videoRef.current.play()
        }
        setReady(true)
        // 권한을 얻은 뒤에야 카메라 이름이 보이므로 여기서 목록을 읽음
        const all = await navigator.mediaDevices.enumerateDevices()
        if (!cancelled) setDevices(all.filter((d) => d.kind === 'videoinput'))
      } catch (e) {
        if (!cancelled) setError(explain(e))
      }
    }

    function stop() {
      streamRef.current?.getTracks().forEach((t) => t.stop())
      streamRef.current = null
    }

    start()
    return () => {
      cancelled = true
      stop()
    }
  }, [deviceId])

  // 캡처한 사진의 object URL 정리
  useEffect(() => () => { if (shot?.url) URL.revokeObjectURL(shot.url) }, [shot])

  function snap() {
    const video = videoRef.current
    if (!video || !video.videoWidth) return
    const canvas = document.createElement('canvas')
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    canvas.getContext('2d').drawImage(video, 0, 0)
    canvas.toBlob(
      (blob) => {
        if (!blob) {
          setError('사진을 만들지 못했습니다. 다시 시도해 주세요.')
          return
        }
        setShot({ blob, url: URL.createObjectURL(blob) })
      },
      'image/jpeg',
      0.92,
    )
  }

  function use() {
    if (!shot) return
    onCapture(shot.blob, `camera_${stamp()}.jpg`)
  }

  return (
    <div className="camera" role="dialog" aria-label="영수증 촬영">
      <div className="camera-head">
        <strong>영수증 촬영</strong>
        {devices.length > 1 && (
          <select value={deviceId} onChange={(e) => { setShot(null); setDeviceId(e.target.value) }} aria-label="카메라 선택">
            <option value="">기본 카메라</option>
            {devices.map((d, i) => (
              <option key={d.deviceId} value={d.deviceId}>{d.label || `카메라 ${i + 1}`}</option>
            ))}
          </select>
        )}
        <button type="button" className="btn" onClick={onClose}>닫기</button>
      </div>

      {error ? (
        <div className="error">{error}</div>
      ) : (
        <div className="camera-view">
          {/* 캡처 후에는 영상 대신 찍은 사진을 보여줌 */}
          <video ref={videoRef} autoPlay playsInline muted style={{ display: shot ? 'none' : 'block' }} />
          {shot && <img src={shot.url} alt="촬영한 영수증" />}
          {!shot && ready && (
            <div className="camera-guide" aria-hidden="true">
              <span>영수증 전체가 틀 안에 들어오게 맞춰 주세요</span>
            </div>
          )}
          {!shot && !ready && <div className="camera-wait">카메라 켜는 중…</div>}
        </div>
      )}

      <div className="camera-bar">
        {shot ? (
          <>
            <button type="button" className="btn" onClick={() => setShot(null)}>다시 찍기</button>
            <button type="button" className="btn primary" onClick={use}>이 사진 사용</button>
          </>
        ) : (
          <button type="button" className="btn primary shutter" onClick={snap} disabled={!ready || !!error}>
            촬영
          </button>
        )}
      </div>
      <p className="hint">
        글씨가 또렷하게 보일 때 찍어야 인식이 잘 됩니다. 그림자가 지지 않게 하고, 흔들리지 않게 잠시 멈춘 뒤 촬영하세요.
      </p>
    </div>
  )
}
