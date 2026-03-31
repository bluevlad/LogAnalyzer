import { useEffect, useState } from 'react'
import { Card, Row, Col, Statistic, Table, Tag, Spin, Alert } from 'antd'
import {
  ApiOutlined,
  BugOutlined,
  WarningOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts'
import { getDashboardSummary, getRequestTimeline } from '../services/api'

interface ServiceSummary {
  service_group: string
  total_requests: number
  status_2xx: number
  status_4xx: number
  status_5xx: number
  error_rate: number
  avg_response_time_ms: number | null
}

interface DashboardData {
  total_services: number
  total_requests_24h: number
  total_errors_24h: number
  error_rate_24h: number
  critical_errors: number
  open_error_groups: number
  services: ServiceSummary[]
}

interface TimelinePoint {
  hour: string
  service_group: string
  total_requests: number
  status_5xx: number
  error_count: number
}

function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [timeline, setTimeline] = useState<TimelinePoint[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      getDashboardSummary(),
      getRequestTimeline(24),
    ]).then(([summaryRes, timelineRes]) => {
      setData(summaryRes.data)
      setTimeline(timelineRes.data)
    }).catch(console.error)
    .finally(() => setLoading(false))
  }, [])

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />
  if (!data) return <Alert type="error" message="데이터 로드 실패" />

  // 타임라인을 시간별로 합산
  const timelineAgg = timeline.reduce<Record<string, { hour: string; requests: number; errors: number }>>((acc, t) => {
    const key = t.hour
    if (!acc[key]) acc[key] = { hour: key, requests: 0, errors: 0 }
    acc[key].requests += t.total_requests
    acc[key].errors += t.error_count
    return acc
  }, {})
  const chartData = Object.values(timelineAgg).sort((a, b) => a.hour.localeCompare(b.hour))

  const columns = [
    { title: '서비스', dataIndex: 'service_group', key: 'service_group' },
    {
      title: '총 요청',
      dataIndex: 'total_requests',
      key: 'total_requests',
      sorter: (a: ServiceSummary, b: ServiceSummary) => a.total_requests - b.total_requests,
      render: (v: number) => v.toLocaleString(),
    },
    {
      title: '2xx',
      dataIndex: 'status_2xx',
      key: 'status_2xx',
      render: (v: number) => <span style={{ color: '#52c41a' }}>{v.toLocaleString()}</span>,
    },
    {
      title: '4xx',
      dataIndex: 'status_4xx',
      key: 'status_4xx',
      render: (v: number) => v > 0 ? <span style={{ color: '#faad14' }}>{v}</span> : 0,
    },
    {
      title: '5xx',
      dataIndex: 'status_5xx',
      key: 'status_5xx',
      render: (v: number) => v > 0 ? <Tag color="red">{v}</Tag> : 0,
    },
    {
      title: '에러율',
      dataIndex: 'error_rate',
      key: 'error_rate',
      render: (v: number) => {
        const color = v >= 5 ? 'red' : v >= 1 ? 'orange' : 'green'
        return <Tag color={color}>{v}%</Tag>
      },
    },
    {
      title: '평균 응답(ms)',
      dataIndex: 'avg_response_time_ms',
      key: 'avg_rt',
      render: (v: number | null) => v ? `${v.toFixed(1)}ms` : '-',
    },
  ]

  return (
    <div>
      <Row gutter={[16, 16]}>
        <Col span={6}>
          <Card>
            <Statistic
              title="활성 서비스"
              value={data.total_services}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="24시간 요청"
              value={data.total_requests_24h}
              prefix={<ApiOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="24시간 오류"
              value={data.total_errors_24h}
              prefix={<BugOutlined />}
              valueStyle={{ color: data.total_errors_24h > 0 ? '#cf1322' : '#3f8600' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Critical 오류"
              value={data.critical_errors}
              prefix={<WarningOutlined />}
              valueStyle={{ color: data.critical_errors > 0 ? '#cf1322' : '#3f8600' }}
            />
          </Card>
        </Col>
      </Row>

      <Card title="시간별 요청/오류 추이 (24h)" style={{ marginTop: 16 }}>
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="hour"
              tickFormatter={(v) => new Date(v).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}
            />
            <YAxis yAxisId="left" />
            <YAxis yAxisId="right" orientation="right" />
            <Tooltip
              labelFormatter={(v) => new Date(v as string).toLocaleString('ko-KR')}
            />
            <Legend />
            <Area yAxisId="left" type="monotone" dataKey="requests" stroke="#1890ff" fill="#1890ff" fillOpacity={0.2} name="요청 수" />
            <Area yAxisId="right" type="monotone" dataKey="errors" stroke="#ff4d4f" fill="#ff4d4f" fillOpacity={0.3} name="오류 수" />
          </AreaChart>
        </ResponsiveContainer>
      </Card>

      <Card title="서비스별 현황" style={{ marginTop: 16 }}>
        <Table
          columns={columns}
          dataSource={data.services}
          rowKey="service_group"
          pagination={false}
          size="middle"
        />
      </Card>
    </div>
  )
}

export default DashboardPage
