// 파일(Blob) → base64 문자열.
//
// 예전에는 FileReader.readAsDataURL 결과를 그대로 썼는데, 가끔 깨진 문자열이 만들어져
// 백엔드가 "image_base64 를 해독할 수 없습니다" 로 거절했습니다 (2026-11-12 서버 로그: 길이는 맞는데
// 소문자·숫자 자리가 빈 문자(\0)로 바뀌어 옴, 다시 누르면 정상). 그래서
//   1) 바이트를 직접 읽어 우리 코드로 인코딩하고
//   2) 보내기 전에 길이·글자를 확인해서, 이상하면 한 번 더 만들고 그래도 이상하면 화면에 알립니다.

const ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
const CODES = Uint8Array.from(ALPHABET, (ch) => ch.charCodeAt(0))
const PAD = '='.charCodeAt(0)
const SHAPE = /^[A-Za-z0-9+/]*={0,2}$/

/** 바이트 배열(Uint8Array) → base64. 브라우저 내장 변환(btoa·FileReader)을 쓰지 않습니다. */
export function encodeBase64(bytes) {
  const n = bytes.length
  const out = new Uint8Array(4 * Math.ceil(n / 3))
  let o = 0
  for (let i = 0; i < n; i += 3) {
    const a = bytes[i]
    const b = i + 1 < n ? bytes[i + 1] : 0
    const c = i + 2 < n ? bytes[i + 2] : 0
    out[o++] = CODES[a >> 2]
    out[o++] = CODES[((a & 3) << 4) | (b >> 4)]
    out[o++] = i + 1 < n ? CODES[((b & 15) << 2) | (c >> 6)] : PAD
    out[o++] = i + 2 < n ? CODES[c & 63] : PAD
  }
  return new TextDecoder('ascii').decode(out)
}

/** 길이와 글자 종류가 base64 로 맞는지 (byteLength 바이트를 변환한 결과여야 함) */
export function isValidBase64(text, byteLength) {
  return typeof text === 'string' && text.length === 4 * Math.ceil(byteLength / 3) && SHAPE.test(text)
}

/** Blob/File → base64 (data: 접두어 없음). 결과가 깨졌으면 한 번 다시 만들고, 그래도 안 되면 오류. */
export async function blobToBase64(blob) {
  let bytes
  try {
    bytes = new Uint8Array(await blob.arrayBuffer())
  } catch {
    throw new Error('사진 파일을 읽지 못했습니다.')
  }
  if (bytes.length === 0) throw new Error('사진 파일이 비어 있습니다.')
  for (let attempt = 0; attempt < 2; attempt++) {
    const text = encodeBase64(bytes)
    if (isValidBase64(text, bytes.length)) return text
  }
  throw new Error('사진을 전송용으로 변환하지 못했습니다. 다시 시도해 주세요.')
}
