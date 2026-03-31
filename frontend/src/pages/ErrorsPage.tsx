import { useEffect, useState, useCallback } from 'react'
import { Card, Row, Col, Statistic, Table, Select, Tag, Button, Space, Spin, Modal, message, Tooltip } from 'antd'
import {
  BugOutlined, WarningOutlined, ExclamationCircleOutlined, CheckCircleOutlined,
  GithubOutlined,
} from '@ant-design/icons'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RTooltip, ResponsiveContainer,
  ScatterChart, Scatter, ZAxis, Cell,
} from 'recharts'
import {
  getErrorSummary, getErrorGroups, getErrorTypeStats, getErrorTimeline,
  updateErrorGroupStatus, createGithubIssue,
} from '../services/api'

interface ErrorSummary {
  total_errors: number
  critical: number
  high: number
  medium: number
  low: number
  open_groups: number
  resolved_groups: number
}

interface ErrorGroup {
  id: number
  fingerprint: string
  container_name: string
  service_group: string
  error_type: string
  severity: string
  sample_message: string
  first_seen: string
  last_seen: string
  occurrence_count: number
  status: string
  github_issue_number: number | null
  github_issue_url: string | null
}

const SEVERITY_COLORS: Record<string, string> = {
  CRITICAL: '#cf1322',
  HIGH: '#fa541c',
  MEDIUM: '#faad14',
  LOW: '#52c41a',
}

const STATUS_COLORS: Record<string, string> = {
  open: 'red',
  acknowledged: 'orange',
  resolved: 'green',
  ignored: 'default',
}

function ErrorsPage() {
  const [summary, setSummary] = useState<ErrorSummary | null>(null)
  const [groups, setGroups] = useState<ErrorGroup[]>([])
  const [typeStats, setTypeStats] = useState<any[]>([])
  const [timeline, setTimeline] = useState<any[]>([])
  const [hours, setHours] = useState(24)
  const [statusFilter, setStatusFilter] = useState<string>('open')
  const [loading, setLoading] = useState(true)

  const loadData = useCallback(() => {
    setLoading(true)
    Promise.all([
      getErrorSummary(hours),
      getErrorGroups({ status: statusFilter || undefined, sort_by: 'occurrence_count' }),
      getErrorTypeStats(hours),
      getErrorTimeline(hours),
    ]).then(([sumRes, grpRes, typeRes, tlRes]) => {
      setSummary(sumRes.data)
      setGroups(grpRes.data)
      setTypeStats(typeRes.data)
      setTimeline(tlRes.data)
    }).catch(console.error)
    .finally(() => setLoading(false))
  }, [hours, statusFilter])

  useEffect(() => { loadData() }, [loadData])

  const handleStatusChange = async (groupId: number, newStatus: string) => {
    try {
      await updateErrorGroupStatus(groupId, newStatus)
      message.success('상태 변경 완료')
      loadData()
    } catch {
      message.error('상태 변경 실패')
    }
  }

  const handleCreateIssue = async (groupId: number) => {
    try {
      const res = await createGithubIssue(groupId)
      if (res.data.status === 'created') {
        message.success(`GitHub Issue #${res.data.number} 생성`)
      } else if (res.data.status === 'already_exists') {
        message.info(`이미 Issue #${res.data.issue_number} 존재`)
      }
      loadData()
    } catch {
      message.error('Issue 생성 실패 (GitHub 토큰 확인)')
    }
  }

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />

  const groupColumns = [
    {
      title: '서비스',
      dataIndex: 'service_group',
      key: 'service_group',
      width: 120,
    },
    {
      title: '오류 유형',
      dataIndex: 'error_type',
      key: 'error_type',
      width: 130,
      render: (v: string) => <Tag>{v}</Tag>,
    },
    {
      title: '심각도',
      dataIndex: 'severity',
      key: 'severity',
      width: 90,
      render: (v: string) => <Tag color={SEVERITY_COLORS[v]}>{v}</Tag>,
    },
    {
      title: '발생 횟수',
      dataIndex: 'occurrence_count',
      key: 'occurrence_count',
      width: 90,
      sorter: (a: ErrorGroup, b: ErrorGroup) => a.occurrence_count - b.occurrence_count,
      render: (v: number) => <span style={{ fontWeight: v >= 10 ? 'bold' : undefined, color: v >= 10 ? '#cf1322' : undefined }}>{v}</span>,
    },
    {
      title: '샘플 메시지',
      dataIndex: 'sample_message',
      key: 'sample_message',
      ellipsis: true,
      render: (v: string) => <Tooltip title={v}><span style={{ fontSize: 12 }}>{v}</span></Tooltip>,
    },
    {
      title: '최종 감지',
      dataIndex: 'last_seen',
      key: 'last_seen',
      width: 150,
      render: (v: string) => new Date(v).toLocaleString('ko-KR'),
    },
    {
      title: '상태',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (v: string, record: ErrorGroup) => (
        <Select
          value={v}
          size="small"
          style={{ width: 110 }}
          onChange={(newStatus) => handleStatusChange(record.id, newStatus)}
        >
          <Select.Option value="open">Open</Select.Option>
          <Select.Option value="acknowledged">확인됨</Select.Option>
          <Select.Option value="resolved">해결됨</Select.Option>
          <Select.Option value="ignored">무시</Select.Option>
        </Select>
      ),
    },
    {
      title: 'GitHub',
      key: 'github',
      width: 80,
      render: (_: any, record: ErrorGroup) => (
        record.github_issue_number ? (
          <a href={record.github_issue_url!} target="_blank" rel="noreferrer">
            #{record.github_issue_number}
          </a>
        ) : (
          <Button
            type="link"
            size="small"
            icon={<GithubOutlined />}
            onClick={() => handleCreateIssue(record.id)}
          >
            생성
          </Button>
        )
      ),
    },
  ]

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', gap: 8 }}>
        <Select value={hours} onChange={setHours} style={{ width: 120 }}>
          <Select.Option value={1}>최근 1시간</Select.Option>
          <Select.Option value={6}>최근 6시간</Select.Option>
          <Select.Option value={24}>최근 24시간</Select.Option>
          <Select.Option value={168}>최근 7일</Select.Option>
        </Select>
        <Select value={statusFilter} onChange={setStatusFilter} style={{ width: 120 }} allowClear placeholder="상태 필터">
          <Select.Option value="open">Open</Select.Option>
          <Select.Option value="acknowledged">확인됨</Select.Option>
          <Select.Option value="resolved">해결됨</Select.Option>
          <Select.Option value="ignored">무시</Select.Option>
        </Select>
      </div>

      {summary && (
        <Row gutter={[16, 16]}>
          <Col span={4}>
            <Card><Statistic title="총 오류" value={summary.total_errors} prefix={<BugOutlined />} /></Card>
          </Col>
          <Col span={4}>
            <Card><Statistic title="CRITICAL" value={summary.critical} valueStyle={{ color: '#cf1322' }} prefix={<ExclamationCircleOutlined />} /></Card>
          </Col>
          <Col span={4}>
            <Card><Statistic title="HIGH" value={summary.high} valueStyle={{ color: '#fa541c' }} prefix={<WarningOutlined />} /></Card>
          </Col>
          <Col span={4}>
            <Card><Statistic title="MEDIUM" value={summary.medium} valueStyle={{ color: '#faad14' }} /></Card>
          </Col>
          <Col span={4}>
            <Card><Statistic title="미해결 그룹" value={summary.open_groups} valueStyle={{ color: '#cf1322' }} /></Card>
          </Col>
          <Col span={4}>
            <Card><Statistic title="해결 그룹" value={summary.resolved_groups} valueStyle={{ color: '#52c41a' }} prefix={<CheckCircleOutlined />} /></Card>
          </Col>
        </Row>
      )}

      <Card title="오류 유형별 분포" style={{ marginTop: 16 }}>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={typeStats}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="error_type" />
            <YAxis />
            <RTooltip />
            <Bar dataKey="count" name="건수">
              {typeStats.map((entry, i) => (
                <Cell key={i} fill={SEVERITY_COLORS[entry.severity] || '#8884d8'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </Card>

      <Card title="오류 그룹" style={{ marginTop: 16 }}>
        <Table
          columns={groupColumns}
          dataSource={groups}
          rowKey="id"
          pagination={{ pageSize: 20 }}
          size="small"
          scroll={{ x: 1200 }}
        />
      </Card>
    </div>
  )
}

export default ErrorsPage
