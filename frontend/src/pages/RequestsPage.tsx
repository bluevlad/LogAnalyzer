import { useEffect, useState } from 'react'
import { Card, Row, Col, Statistic, Table, Select, Tag, Spin } from 'antd'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, Cell,
} from 'recharts'
import {
  getRequestSummary, getRequestsByService, getTopEndpoints, getSlowRequests,
} from '../services/api'

interface RequestStats {
  total_requests: number
  status_2xx: number
  status_3xx: number
  status_4xx: number
  status_5xx: number
  avg_response_time_ms: number | null
  error_rate: number
}

interface EndpointStat {
  path: string
  method: string
  service_group: string
  total_requests: number
  error_count: number
  error_rate: number
  avg_response_time_ms: number | null
  max_response_time_ms: number | null
}

interface SlowRequest {
  id: number
  service_group: string
  container_name: string
  timestamp: string
  method: string
  path: string
  status_code: number
  response_time_ms: number
}

const METHOD_COLORS: Record<string, string> = {
  GET: '#52c41a', POST: '#1890ff', PUT: '#faad14', DELETE: '#ff4d4f', PATCH: '#722ed1',
}

function RequestsPage() {
  const [stats, setStats] = useState<RequestStats | null>(null)
  const [serviceStats, setServiceStats] = useState<any[]>([])
  const [endpoints, setEndpoints] = useState<EndpointStat[]>([])
  const [slowReqs, setSlowReqs] = useState<SlowRequest[]>([])
  const [hours, setHours] = useState(24)
  const [sortBy, setSortBy] = useState('count')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    Promise.all([
      getRequestSummary(hours),
      getRequestsByService(hours),
      getTopEndpoints(hours, sortBy),
      getSlowRequests(hours),
    ]).then(([summaryRes, serviceRes, endpointRes, slowRes]) => {
      setStats(summaryRes.data)
      setServiceStats(serviceRes.data)
      setEndpoints(endpointRes.data)
      setSlowReqs(slowRes.data)
    }).catch(console.error)
    .finally(() => setLoading(false))
  }, [hours, sortBy])

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />

  const statusChartData = stats ? [
    { name: '2xx', value: stats.status_2xx, color: '#52c41a' },
    { name: '3xx', value: stats.status_3xx, color: '#1890ff' },
    { name: '4xx', value: stats.status_4xx, color: '#faad14' },
    { name: '5xx', value: stats.status_5xx, color: '#ff4d4f' },
  ] : []

  const endpointColumns = [
    {
      title: 'Method',
      dataIndex: 'method',
      key: 'method',
      width: 80,
      render: (m: string) => <Tag color={METHOD_COLORS[m] || 'default'}>{m}</Tag>,
    },
    { title: '경로', dataIndex: 'path', key: 'path', ellipsis: true },
    { title: '서비스', dataIndex: 'service_group', key: 'service_group' },
    {
      title: '요청 수',
      dataIndex: 'total_requests',
      key: 'total_requests',
      render: (v: number) => v.toLocaleString(),
    },
    {
      title: '에러',
      dataIndex: 'error_count',
      key: 'error_count',
      render: (v: number) => v > 0 ? <Tag color="red">{v}</Tag> : 0,
    },
    {
      title: '에러율',
      dataIndex: 'error_rate',
      key: 'error_rate',
      render: (v: number) => {
        const color = v >= 10 ? 'red' : v >= 1 ? 'orange' : 'green'
        return <Tag color={color}>{v}%</Tag>
      },
    },
    {
      title: '평균(ms)',
      dataIndex: 'avg_response_time_ms',
      key: 'avg_rt',
      render: (v: number | null) => v ? v.toFixed(1) : '-',
    },
    {
      title: '최대(ms)',
      dataIndex: 'max_response_time_ms',
      key: 'max_rt',
      render: (v: number | null) => v ? <span style={{ color: v > 1000 ? '#cf1322' : undefined }}>{v.toFixed(0)}</span> : '-',
    },
  ]

  const slowColumns = [
    { title: '서비스', dataIndex: 'service_group', key: 'service_group' },
    {
      title: 'Method',
      dataIndex: 'method',
      key: 'method',
      render: (m: string) => <Tag color={METHOD_COLORS[m]}>{m}</Tag>,
    },
    { title: '경로', dataIndex: 'path', key: 'path', ellipsis: true },
    {
      title: '상태',
      dataIndex: 'status_code',
      key: 'status_code',
      render: (v: number) => <Tag color={v >= 500 ? 'red' : v >= 400 ? 'orange' : 'green'}>{v}</Tag>,
    },
    {
      title: '응답시간(ms)',
      dataIndex: 'response_time_ms',
      key: 'response_time_ms',
      render: (v: number) => <span style={{ color: '#cf1322', fontWeight: 'bold' }}>{v.toFixed(0)}</span>,
    },
    {
      title: '시각',
      dataIndex: 'timestamp',
      key: 'timestamp',
      render: (v: string) => new Date(v).toLocaleString('ko-KR'),
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
      </div>

      {stats && (
        <Row gutter={[16, 16]}>
          <Col span={4}><Card><Statistic title="총 요청" value={stats.total_requests} /></Card></Col>
          <Col span={4}><Card><Statistic title="2xx" value={stats.status_2xx} valueStyle={{ color: '#52c41a' }} /></Card></Col>
          <Col span={4}><Card><Statistic title="4xx" value={stats.status_4xx} valueStyle={{ color: '#faad14' }} /></Card></Col>
          <Col span={4}><Card><Statistic title="5xx" value={stats.status_5xx} valueStyle={{ color: '#cf1322' }} /></Card></Col>
          <Col span={4}><Card><Statistic title="에러율" value={stats.error_rate} suffix="%" /></Card></Col>
          <Col span={4}><Card><Statistic title="평균 응답" value={stats.avg_response_time_ms?.toFixed(1) || '-'} suffix="ms" /></Card></Col>
        </Row>
      )}

      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col span={12}>
          <Card title="응답코드 분포">
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={statusChartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="value" name="건수">
                  {statusChartData.map((entry, i) => (
                    <Cell key={i} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col span={12}>
          <Card title="서비스별 트래픽">
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={serviceStats} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" />
                <YAxis dataKey="service_group" type="category" width={120} />
                <Tooltip />
                <Legend />
                <Bar dataKey="status_2xx" stackId="a" fill="#52c41a" name="2xx" />
                <Bar dataKey="status_4xx" stackId="a" fill="#faad14" name="4xx" />
                <Bar dataKey="status_5xx" stackId="a" fill="#ff4d4f" name="5xx" />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>

      <Card
        title="엔드포인트 TOP 20"
        style={{ marginTop: 16 }}
        extra={
          <Select value={sortBy} onChange={setSortBy} style={{ width: 140 }}>
            <Select.Option value="count">요청 수</Select.Option>
            <Select.Option value="error_rate">에러율</Select.Option>
            <Select.Option value="avg_rt">응답시간</Select.Option>
          </Select>
        }
      >
        <Table
          columns={endpointColumns}
          dataSource={endpoints}
          rowKey={(r) => `${r.service_group}-${r.method}-${r.path}`}
          pagination={false}
          size="small"
        />
      </Card>

      <Card title="느린 요청 (1초+)" style={{ marginTop: 16 }}>
        <Table
          columns={slowColumns}
          dataSource={slowReqs}
          rowKey="id"
          pagination={{ pageSize: 20 }}
          size="small"
        />
      </Card>
    </div>
  )
}

export default RequestsPage
