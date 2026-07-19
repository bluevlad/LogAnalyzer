// 관리 대상 서비스 (백엔드 LA_MANAGED_SERVICES와 동일 순서)
export interface ManagedService {
  name: string
  color: string
}

export const MANAGED_SERVICES: ManagedService[] = [
  { name: 'AllergyInsight', color: '#f43f5e' },
  { name: 'SkillRadar', color: '#8b5cf6' },
  { name: 'NewsLetterPlatform', color: '#ec4899' },
]

export const SERVICE_COLORS: Record<string, string> = Object.fromEntries(
  MANAGED_SERVICES.map((s) => [s.name, s.color]),
)

export const SERVICE_FILTER_OPTIONS = [
  { value: '', label: '전체 서비스' },
  ...MANAGED_SERVICES.map((s) => ({ value: s.name, label: s.name })),
]
