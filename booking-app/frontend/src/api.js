export async function api(path, options = {}) {
  const response = await fetch('/api' + path, {
    credentials: 'same-origin',
    ...options,
    headers: { 'Content-Type': 'application/json', ...options.headers },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  })
  if (!response.headers.get('Content-Type')?.includes('application/json')) {
    throw new Error('서버에 연결하지 못했습니다. Python 서버가 실행 중인지 확인해 주세요.')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.error || '요청을 처리하지 못했습니다.')
  return data
}
