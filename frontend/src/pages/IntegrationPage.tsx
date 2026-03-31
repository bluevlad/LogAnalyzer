import { useState } from 'react'
import { Card, Row, Col, Button, Space, Tag, message, Descriptions, Alert, Typography } from 'antd'
import {
  GithubOutlined, SendOutlined, SyncOutlined, CheckCircleOutlined,
} from '@ant-design/icons'
import { pushToQaDashboard, reportToStandup, getHealth } from '../services/api'

const { Title, Paragraph, Text } = Typography

function IntegrationPage() {
  const [loading, setLoading] = useState<string | null>(null)
  const [healthStatus, setHealthStatus] = useState<any>(null)

  const handleQaPush = async () => {
    setLoading('qa')
    try {
      const res = await pushToQaDashboard()
      if (res.data.status === 'sent') {
        message.success(`${res.data.groups_count}개 오류 그룹 QA Dashboard 전송 완료`)
      } else if (res.data.status === 'no_data') {
        message.info('전송할 오류 그룹이 없습니다')
      } else {
        message.warning('전송 실패 — QA Dashboard API 키를 확인하세요')
      }
    } catch {
      message.error('QA Dashboard 연동 실패')
    }
    setLoading(null)
  }

  const handleStandupReport = async () => {
    setLoading('standup')
    try {
      const res = await reportToStandup()
      if (res.data.status === 'sent') {
        message.success(`${res.data.groups_count}개 수정 항목 StandUp 보고 완료`)
      } else if (res.data.status === 'no_data') {
        message.info('보고할 해결 항목이 없습니다')
      } else {
        message.warning('보고 실패 — StandUp API 키를 확인하세요')
      }
    } catch {
      message.error('StandUp 연동 실패')
    }
    setLoading(null)
  }

  const handleHealthCheck = async () => {
    setLoading('health')
    try {
      const res = await getHealth()
      setHealthStatus(res.data)
    } catch {
      setHealthStatus({ status: 'error', database: 'disconnected' })
    }
    setLoading(null)
  }

  return (
    <div>
      <Title level={4}>외부 시스템 연동 관리</Title>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={8}>
          <Card
            title={<><GithubOutlined /> GitHub Issue</>}
            hoverable
          >
            <Paragraph>
              CRITICAL/HIGH 오류 그룹에 대해 GitHub Issue를 자동 생성합니다.
              QA-AGENT-META 포맷이 포함되어 Auto-Tobe-Agent가 자동 수정합니다.
            </Paragraph>
            <Descriptions column={1} size="small" bordered>
              <Descriptions.Item label="트리거">일일 리포트 (06:00) 또는 오류 페이지에서 수동</Descriptions.Item>
              <Descriptions.Item label="대상">발생 3회 이상 CRITICAL/HIGH 미해결 오류</Descriptions.Item>
              <Descriptions.Item label="연결">Auto-Tobe-Agent → QA Agent 재검증</Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>

        <Col span={8}>
          <Card
            title={<><SendOutlined /> QA Dashboard</>}
            hoverable
            actions={[
              <Button
                type="primary"
                icon={<SyncOutlined spin={loading === 'qa'} />}
                onClick={handleQaPush}
                loading={loading === 'qa'}
              >
                수동 전송
              </Button>,
            ]}
          >
            <Paragraph>
              미해결 오류 그룹을 QA Dashboard에 점검 항목으로 전송합니다.
              QA Dashboard의 ingest API를 통해 run 데이터로 등록됩니다.
            </Paragraph>
            <Descriptions column={1} size="small" bordered>
              <Descriptions.Item label="트리거">일일 리포트 (06:00) 또는 수동</Descriptions.Item>
              <Descriptions.Item label="포맷">QA Agent run JSON 호환</Descriptions.Item>
              <Descriptions.Item label="인증">Bearer API Key</Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>

        <Col span={8}>
          <Card
            title={<><CheckCircleOutlined /> StandUp</>}
            hoverable
            actions={[
              <Button
                type="primary"
                icon={<SyncOutlined spin={loading === 'standup'} />}
                onClick={handleStandupReport}
                loading={loading === 'standup'}
              >
                수동 보고
              </Button>,
            ]}
          >
            <Paragraph>
              해결된 오류 그룹을 StandUp에 work item으로 등록합니다.
              일일/주간 리포트에 "로그 기반 수정 현황"으로 포함됩니다.
            </Paragraph>
            <Descriptions column={1} size="small" bordered>
              <Descriptions.Item label="트리거">일일 리포트 (06:00) 또는 수동</Descriptions.Item>
              <Descriptions.Item label="대상">status=resolved 오류 그룹</Descriptions.Item>
              <Descriptions.Item label="카테고리">bug-fix</Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
      </Row>

      <Card title="시스템 상태" style={{ marginTop: 24 }}>
        <Space direction="vertical">
          <Button onClick={handleHealthCheck} loading={loading === 'health'}>
            헬스체크 실행
          </Button>
          {healthStatus && (
            <Descriptions bordered size="small">
              <Descriptions.Item label="상태">
                <Tag color={healthStatus.status === 'ok' ? 'green' : 'red'}>
                  {healthStatus.status}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="데이터베이스">
                <Tag color={healthStatus.database === 'connected' ? 'green' : 'red'}>
                  {healthStatus.database}
                </Tag>
              </Descriptions.Item>
            </Descriptions>
          )}
        </Space>
      </Card>

      <Card title="연동 플로우" style={{ marginTop: 24 }}>
        <Alert
          type="info"
          message="자동 연동 파이프라인"
          description={
            <pre style={{ fontSize: 12, margin: 0 }}>{`Docker Containers (24개)
    │ docker.sock (5분마다)
    ▼
┌─────────────┐
│ LogAnalyzer  │──── 대시보드: 요청 분석 + 오류 리스트/집계
└──────┬──────┘
       │
       ├──→ GitHub Issue (QA-AGENT-META 포함)
       │        ├──→ Auto-Tobe-Agent (자동 수정)
       │        └──→ QA Agent (재검증, 22:00)
       │
       ├──→ StandUp (수정 완료 → work item 등록)
       │        └──→ Report-Agent (일일/주간 리포트)
       │
       └──→ QA Dashboard (점검 항목 직접 등록)`}</pre>
          }
        />
      </Card>
    </div>
  )
}

export default IntegrationPage
