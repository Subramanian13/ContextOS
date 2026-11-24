export const parseDate = (value: string) => new Date(value.includes('T') ? value : `${value}T12:00:00`)

export const formatDate = (value: string | null, options: Intl.DateTimeFormatOptions = { month: 'short', day: 'numeric', year: 'numeric' }) =>
  value ? new Intl.DateTimeFormat('en-US', options).format(parseDate(value)) : 'Not forecast'

export function calendarDaysBetween(start: string, end: string) {
  return Math.round((parseDate(end).getTime() - parseDate(start).getTime()) / 86_400_000)
}

export function workingDates(startValue: string, endValue: string) {
  const dates: string[] = []
  const cursor = parseDate(startValue)
  const end = parseDate(endValue)
  while (cursor <= end) {
    if (cursor.getDay() !== 0 && cursor.getDay() !== 6) dates.push(cursor.toISOString().slice(0, 10))
    cursor.setDate(cursor.getDate() + 1)
  }
  return dates
}
