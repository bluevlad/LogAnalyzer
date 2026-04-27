import { Routes, Route, useNavigate, useLocation } from 'react-router-dom'
import { Layout, Menu, Typography } from 'antd'
import {
  DashboardOutlined,
  ApiOutlined,
  BugOutlined,
  LinkOutlined,
} from '@ant-design/icons'
import DashboardPage from './pages/DashboardPage'
import RequestsPage from './pages/RequestsPage'
import ErrorsPage from './pages/ErrorsPage'
import IntegrationPage from './pages/IntegrationPage'
import GatewayLanding from './pages/gateway-landing/GatewayLanding'

const { Header, Content, Sider } = Layout
const { Title } = Typography

const menuItems = [
  { key: '/dashboard', icon: <DashboardOutlined />, label: '대시보드' },
  { key: '/requests', icon: <ApiOutlined />, label: 'Request 분석' },
  { key: '/errors', icon: <BugOutlined />, label: '오류 로그' },
  { key: '/integration', icon: <LinkOutlined />, label: '연동 관리' },
]

function ConsoleLayout({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate()
  const location = useLocation()

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider theme="dark" width={200}>
        <div style={{ padding: '16px', textAlign: 'center' }}>
          <Title level={4} style={{ color: '#fff', margin: 0 }}>
            LogAnalyzer
          </Title>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header style={{ background: '#fff', padding: '0 24px', borderBottom: '1px solid #f0f0f0' }}>
          <Title level={4} style={{ margin: '16px 0' }}>
            Docker Log Analysis Service
          </Title>
        </Header>
        <Content style={{ margin: '24px', minHeight: 280 }}>{children}</Content>
      </Layout>
    </Layout>
  )
}

function App() {
  return (
    <Routes>
      <Route path="/" element={<GatewayLanding />} />
      <Route path="/dashboard" element={<ConsoleLayout><DashboardPage /></ConsoleLayout>} />
      <Route path="/requests" element={<ConsoleLayout><RequestsPage /></ConsoleLayout>} />
      <Route path="/errors" element={<ConsoleLayout><ErrorsPage /></ConsoleLayout>} />
      <Route path="/integration" element={<ConsoleLayout><IntegrationPage /></ConsoleLayout>} />
    </Routes>
  )
}

export default App
