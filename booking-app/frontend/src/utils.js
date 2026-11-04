export const won = n => n.toLocaleString('ko-KR') + '원'
export const photo = (id, width = 600) => `https://images.unsplash.com/${id}?auto=format&fit=crop&w=${width}&q=80`
export const paymentLabels = { PENDING: '결제 대기', COMPLETED: '결제 완료', CANCELLED: '결제 취소' }
export const koreanTime = value => new Date(value).toLocaleString('ko-KR', {
  timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit',
  hour: '2-digit', minute: '2-digit', hour12: false,
})
export function availableDates(show) {
  return Array.from({ length: show.days }, (_, i) => {
    const date = new Date(`${show.start}T12:00:00`)
    date.setDate(date.getDate() + i)
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
  })
}
