import { Link } from 'react-router-dom';
import './GatewayLanding.css';

interface Feature {
  icon: string;
  name: string;
  desc: string;
  to: string;
  external?: boolean;
}

const FEATURES: Feature[] = [
  {
    icon: '📊',
    name: '로그 대시보드',
    desc: '전체 서비스 로그 실시간 스트리밍 — 서비스/레벨별 집계와 추이를 한 화면에',
    to: '/dashboard',
  },
  {
    icon: '🔎',
    name: 'Request 분석',
    desc: 'API 요청 단위로 응답시간·상태코드·엔드포인트 분포를 분석',
    to: '/requests',
  },
  {
    icon: '🐛',
    name: '오류 로그',
    desc: 'ERROR/WARN 레벨 로그를 패턴별로 묶어 빈도·트렌드·원인을 추적',
    to: '/errors',
  },
  {
    icon: '🔗',
    name: '연동 관리',
    desc: '로그 수집 대상 컨테이너·서비스 연동 현황 관리',
    to: '/integration',
  },
  {
    icon: '🔌',
    name: 'API Docs',
    desc: 'Swagger UI 기반 OpenAPI 명세 — 로그 조회/검색 REST API',
    to: '/api/docs',
    external: true,
  },
];

interface Tech { name: string; dot: string; }
const TECH_STACK: Tech[] = [
  { name: 'React 18', dot: '#61dafb' },
  { name: 'TypeScript', dot: '#3178c6' },
  { name: 'Ant Design', dot: '#1677ff' },
  { name: 'FastAPI', dot: '#009688' },
  { name: 'PostgreSQL', dot: '#336791' },
  { name: 'Docker Log API', dot: '#2496ed' },
];

interface Connected { name: string; role: string; href: string; dot: string; }
const CONNECTED_SERVICES: Connected[] = [
  { name: 'AllergyInsight', role: '로그 수집 대상', href: 'https://allergy.unmong.com', dot: '#f43f5e' },
  { name: 'EduFit', role: '로그 수집 대상', href: 'https://edufit.unmong.com', dot: '#22c55e' },
  { name: 'NewsLetterPlatform', role: '로그 수집 대상', href: 'https://newsletter.unmong.com', dot: '#ec4899' },
  { name: 'StandUp', role: '로그 수집 대상', href: 'https://standup.unmong.com', dot: '#14b8a6' },
  { name: 'InfraWatcher', role: '컨테이너 모니터링', href: 'https://infrawatcher.unmong.com', dot: '#06b6d4' },
  { name: 'QA-Agent', role: '품질 자동 테스트', href: 'https://qadashboard.unmong.com', dot: '#8b5cf6' },
];

interface FeatureCardProps { feature: Feature; }

const FeatureCard = ({ feature }: FeatureCardProps) => {
  const inner = (
    <>
      <span className="sl-feature-icon" aria-hidden="true">{feature.icon}</span>
      <div className="sl-feature-name">{feature.name}</div>
      <div className="sl-feature-desc">{feature.desc}</div>
      <span className="sl-feature-tag sl-feature-tag--public">🌐 공개</span>
    </>
  );

  if (feature.external) {
    return (
      <a className="sl-feature" data-locked="false" href={feature.to} target="_blank" rel="noopener noreferrer">
        {inner}
      </a>
    );
  }
  return (
    <Link className="sl-feature" data-locked="false" to={feature.to}>
      {inner}
    </Link>
  );
};

const GatewayLanding = () => {
  return (
    <div className="gateway-landing-root">
      <div className="sl-container">
        <section className="sl-hero">
          <h1>LogAnalyzer</h1>
          <p className="tagline">Log Analysis · Anomaly Detection</p>
          <p className="desc">
            전체 서비스의 Docker 컨테이너 로그를 수집·분석하여 이상 징후를 탐지하는 로그 분석 플랫폼 — 실시간 검색, 패턴 기반 알림, 트렌드 시각화 제공
          </p>
        </section>

        <section className="sl-section">
          <div className="sl-section-title">Features</div>
          <div className="sl-features">
            {FEATURES.map((feature) => (
              <FeatureCard key={feature.name} feature={feature} />
            ))}
          </div>
        </section>

        <section className="sl-section sl-arch">
          <div className="sl-section-title">Architecture</div>
          <div className="sl-arch-diagram">
            <div className="sl-arch-node">
              <div className="sl-arch-node-label">Docker Engine</div>
              <div className="sl-arch-node-tech">Log API<br /><span className="sl-arch-node-tech-sub">컨테이너 로그</span></div>
            </div>
            <div className="sl-arch-arrow">→</div>
            <div className="sl-arch-node highlight">
              <div className="sl-arch-node-label">Backend</div>
              <div className="sl-arch-node-tech">FastAPI<br /><span className="sl-arch-node-tech-sub">파서 · 분석</span></div>
            </div>
            <div className="sl-arch-arrow">→</div>
            <div className="sl-arch-node">
              <div className="sl-arch-node-label">Database</div>
              <div className="sl-arch-node-tech">PostgreSQL<br /><span className="sl-arch-node-tech-sub">로그 인덱스</span></div>
            </div>
            <div className="sl-arch-arrow">←</div>
            <div className="sl-arch-node">
              <div className="sl-arch-node-label">Frontend</div>
              <div className="sl-arch-node-tech">React + AntD<br /><span className="sl-arch-node-tech-sub">검색 · 시각화</span></div>
            </div>
          </div>
        </section>

        <section className="sl-section sl-flow">
          <div className="sl-section-title">Service Flow</div>
          <div className="sl-flow-steps">
            <div className="sl-flow-step">
              <div className="sl-flow-step-num">1</div>
              <div className="sl-flow-step-label">로그 수집</div>
              <div className="sl-flow-step-desc">Docker Log API</div>
            </div>
            <div className="sl-flow-arrow">→</div>
            <div className="sl-flow-step">
              <div className="sl-flow-step-num">2</div>
              <div className="sl-flow-step-label">파싱/저장</div>
              <div className="sl-flow-step-desc">구조화 · 인덱싱</div>
            </div>
            <div className="sl-flow-arrow">→</div>
            <div className="sl-flow-step">
              <div className="sl-flow-step-num">3</div>
              <div className="sl-flow-step-label">패턴 분석</div>
              <div className="sl-flow-step-desc">이상 징후 탐지</div>
            </div>
            <div className="sl-flow-arrow">→</div>
            <div className="sl-flow-step">
              <div className="sl-flow-step-num">4</div>
              <div className="sl-flow-step-label">대시보드</div>
              <div className="sl-flow-step-desc">검색 · 시각화</div>
            </div>
          </div>
        </section>

        <section className="sl-section sl-tech">
          <div className="sl-section-title">Tech Stack</div>
          <div className="sl-tech-list">
            {TECH_STACK.map((tech) => (
              <span className="sl-tech-badge" key={tech.name}>
                <span className="sl-tech-dot" style={{ background: tech.dot }} />
                {tech.name}
              </span>
            ))}
          </div>
        </section>

        <section className="sl-section sl-connected">
          <div className="sl-section-title">Log Sources</div>
          <div className="sl-connected-grid">
            {CONNECTED_SERVICES.map((svc) => (
              <a
                key={svc.name}
                href={svc.href}
                target="_blank"
                rel="noopener noreferrer"
                className="sl-connected-card"
              >
                <span className="sl-connected-dot" style={{ background: svc.dot }} />
                <div className="sl-connected-info">
                  <div className="sl-connected-name">{svc.name}</div>
                  <div className="sl-connected-role">{svc.role}</div>
                </div>
                <span className="sl-connected-arrow">→</span>
              </a>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
};

export default GatewayLanding;
