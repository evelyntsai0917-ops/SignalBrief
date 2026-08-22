<script setup>
import { computed, onMounted, ref } from 'vue'

const signals = ref([])
const updatedAt = ref('')
const loading = ref(true)
const errorMessage = ref('')
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL

const investmentTopics = [
  {
    key: 'geopolitics',
    label: 'Geopolitics & Global Risk',
    zh: '地緣政治與全球風險',
    description: 'Conflict, trade, sanctions and global events moving markets.',
  },
  {
    key: 'macro',
    label: 'Macro & Policy',
    zh: '總體經濟與政策',
    description: 'Rates, inflation, central banks and economic policy.',
  },
  {
    key: 'ai-semiconductor',
    label: 'AI & Semiconductor',
    zh: 'AI 與半導體供應鏈',
    description: 'AI infrastructure, chips, supply chains and capital spending.',
  },
  {
    key: 'company',
    label: 'Major Companies',
    zh: '公司重大事件',
    description: 'Earnings, M&A, strategy and company-level market events.',
  },
]

const industryTopics = [
  {
    label: 'Artificial Intelligence',
    zh: '人工智慧',
    description: 'Models, applications, infrastructure and the evolving AI ecosystem.',
  },
  {
    label: 'Semiconductors',
    zh: '半導體',
    description: 'Foundries, HBM, advanced packaging and the global chip supply chain.',
  },
  {
    label: 'Cloud & Data Center',
    zh: '雲端與資料中心',
    description: 'Cloud infrastructure, data centers, networking and AI compute.',
  },
  {
    label: 'Cybersecurity',
    zh: '資安',
    description: 'Threats, platforms and structural changes in digital security.',
  },
  {
    label: 'FinTech / Digital Finance',
    zh: '金融科技與數位金融',
    description: 'Payments, digital banking and financial infrastructure.',
  },
]

const formattedUpdatedAt = computed(() => {
  if (!updatedAt.value) return ''

  return new Date(updatedAt.value).toLocaleString('zh-TW', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
})

const sortedSignals = computed(() => {
  return [...signals.value].sort(
    (a, b) => (a.top_rank ?? 99) - (b.top_rank ?? 99),
  )
})

function normalizeSubcategory(signal) {
  return String(signal.subcategory || '').toLowerCase()
}

function getTopicKey(signal) {
  const value = normalizeSubcategory(signal)

  if (
    value.includes('geo') ||
    value.includes('war') ||
    value.includes('global risk')
  ) {
    return 'geopolitics'
  }

  if (
    value.includes('macro') ||
    value.includes('economic') ||
    value.includes('policy') ||
    value.includes('fed') ||
    value.includes('rate')
  ) {
    return 'macro'
  }

  if (
    value.includes('ai') ||
    value.includes('semi') ||
    value.includes('chip')
  ) {
    return 'ai-semiconductor'
  }

  return 'company'
}

function getTopicSignal(topicKey) {
  return sortedSignals.value.find(
    (signal) => getTopicKey(signal) === topicKey,
  )
}

function displayCategory(signal) {
  const key = getTopicKey(signal)

  const labels = {
    geopolitics: 'Geopolitics',
    macro: 'Macro & Policy',
    'ai-semiconductor': 'AI & Semiconductor',
    company: 'Major Company',
  }

  return labels[key]
}

function formatPublishedAt(value) {
  if (!value) return ''

  return new Date(value).toLocaleString('zh-TW', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

onMounted(async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/signals`)

    if (!response.ok) {
      throw new Error('無法讀取 SignalBrief 最新情報')
    }

    const data = await response.json()

    signals.value = data.signals || []
    updatedAt.value = data.updated_at || ''
  } catch (error) {
    errorMessage.value = error.message || '載入失敗'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="app-shell">
    <header class="site-header">
      <div class="brand">
        <div class="brand-mark">S</div>

        <div>
          <div class="brand-name">SignalBrief</div>
          <div class="brand-subtitle">
            Investment & Industry Intelligence
          </div>
        </div>
      </div>

      <div class="header-status">
        <span class="status-dot"></span>

        <span v-if="formattedUpdatedAt">
          Updated {{ formattedUpdatedAt }}
        </span>

        <span v-else>
          Daily intelligence
        </span>
      </div>
    </header>

    <main class="page">
      <section class="hero">
        <div class="eyebrow">DAILY BRIEFING</div>

        <h1>
          Understand what matters.<br />
          <span>Before the market moves.</span>
        </h1>

        <p class="hero-copy">
          SignalBrief filters market-moving events and emerging industry
          developments into the signals worth your attention.
        </p>
      </section>

      <section v-if="loading" class="system-message">
        <div class="loader"></div>
        <div>
          <strong>Loading today's signals</strong>
          <p>正在讀取最新投資情報。</p>
        </div>
      </section>

      <section v-else-if="errorMessage" class="system-message error">
        <div>
          <strong>Unable to load signals</strong>
          <p>{{ errorMessage }}</p>
        </div>
      </section>

      <template v-else>
        <section class="intelligence-grid">
          <!-- INVESTMENT -->
          <div class="intelligence-panel investment-panel">
            <div class="panel-header">
              <div>
                <div class="section-kicker">INVESTMENT INTELLIGENCE</div>
                <h2>Today's Top 3</h2>
                <p>今天最值得投資人關注的市場事件</p>
              </div>

              <span class="live-pill">LIVE</span>
            </div>

            <div v-if="sortedSignals.length" class="top-signals">
              <article
                v-for="(signal, index) in sortedSignals.slice(0, 3)"
                :key="signal.id || signal.source_url"
                class="signal-card"
              >
                <div class="signal-rank">
                  {{ String(index + 1).padStart(2, '0') }}
                </div>

                <div class="signal-content">
                  <div class="signal-meta">
                    <span class="category-pill">
                      {{ displayCategory(signal) }}
                    </span>

                    <span
                      v-if="signal.importance_score !== undefined"
                      class="impact-score"
                    >
                      Impact {{ signal.importance_score }}
                    </span>
                  </div>

                  <h3>
                    <a
                      :href="signal.source_url"
                      target="_blank"
                      rel="noreferrer"
                    >
                      {{ signal.title }}
                    </a>
                  </h3>

                  <p
                    v-if="signal.summary_points?.length"
                    class="signal-summary"
                  >
                    {{ signal.summary_points[0] }}
                  </p>

                  <div
                    v-if="signal.impact_path"
                    class="impact-path"
                  >
                    <span>Impact path</span>
                    {{ signal.impact_path }}
                  </div>

                  <div class="source-row">
                    <span>{{ signal.source_name }}</span>

                    <span v-if="signal.published_at">
                      {{ formatPublishedAt(signal.published_at) }}
                    </span>

                    <a
                      :href="signal.source_url"
                      target="_blank"
                      rel="noreferrer"
                    >
                      Read source ↗
                    </a>
                  </div>
                </div>
              </article>
            </div>

            <div v-else class="empty-state">
              No investment signals available yet.
            </div>
          </div>

          <!-- INDUSTRY -->
          <div class="intelligence-panel industry-panel">
            <div class="panel-header">
              <div>
                <div class="section-kicker">INDUSTRY FRONTIER</div>
                <h2>Today's Top 3</h2>
                <p>值得長期追蹤的產業結構與技術趨勢</p>
              </div>

              <span class="soon-pill">COMING SOON</span>
            </div>

            <div class="industry-placeholder">
              <div class="radar-visual">
                <div class="radar-ring ring-1"></div>
                <div class="radar-ring ring-2"></div>
                <div class="radar-ring ring-3"></div>
                <div class="radar-center"></div>
              </div>

              <div class="placeholder-copy">
                <span>INDUSTRY SIGNAL ENGINE</span>
                <h3>Industry intelligence is being built.</h3>
                <p>
                  SignalBrief will track structural developments across AI,
                  semiconductors, cloud infrastructure, cybersecurity and
                  digital finance.
                </p>
              </div>
            </div>
          </div>
        </section>

        <!-- EXPLORE -->
        <section class="explore-section">
          <div class="explore-heading">
            <div>
              <div class="eyebrow">EXPLORE BY TOPIC</div>
              <h2>Dive deeper into the signals shaping markets and industries.</h2>
            </div>
          </div>

          <div class="topic-columns">
            <!-- INVESTMENT TOPICS -->
            <div class="topic-column">
              <div class="topic-column-heading">
                <span class="column-number">01</span>

                <div>
                  <div class="section-kicker">
                    INVESTMENT INTELLIGENCE
                  </div>
                  <h3>投資情報</h3>
                </div>
              </div>

              <div class="topic-list">
                <article
                  v-for="topic in investmentTopics"
                  :key="topic.key"
                  class="topic-card"
                >
                  <div class="topic-card-header">
                    <div>
                      <h4>{{ topic.label }}</h4>
                      <span>{{ topic.zh }}</span>
                    </div>

                    <span
                      v-if="getTopicSignal(topic.key)"
                      class="available-dot"
                    ></span>
                    <span v-else class="coming-tag">
                      Coming soon
                    </span>
                  </div>

                  <p class="topic-description">
                    {{ topic.description }}
                  </p>

                  <template v-if="getTopicSignal(topic.key)">
                    <div class="topic-story">
                      <span>TOP SIGNAL</span>

                      <a
                        :href="getTopicSignal(topic.key).source_url"
                        target="_blank"
                        rel="noreferrer"
                      >
                        {{ getTopicSignal(topic.key).title }}
                      </a>
                    </div>
                  </template>

                  <div v-else class="topic-empty">
                    More signals will appear here as coverage expands.
                  </div>
                </article>
              </div>
            </div>

            <!-- INDUSTRY TOPICS -->
            <div class="topic-column industry-topic-column">
              <div class="topic-column-heading">
                <span class="column-number">02</span>

                <div>
                  <div class="section-kicker">
                    INDUSTRY FRONTIER
                  </div>
                  <h3>產業最前線</h3>
                </div>
              </div>

              <div class="topic-list">
                <article
                  v-for="topic in industryTopics"
                  :key="topic.label"
                  class="topic-card industry-topic-card"
                >
                  <div class="topic-card-header">
                    <div>
                      <h4>{{ topic.label }}</h4>
                      <span>{{ topic.zh }}</span>
                    </div>

                    <span class="coming-tag">
                      Coming soon
                    </span>
                  </div>

                  <p class="topic-description">
                    {{ topic.description }}
                  </p>

                  <div class="topic-empty">
                    Industry monitoring module in development.
                  </div>
                </article>
              </div>
            </div>
          </div>
        </section>
      </template>
    </main>

    <footer>
      <div class="brand-name">SignalBrief</div>
      <p>
        Intelligence for people who want to understand what matters,
        without reading everything.
      </p>
    </footer>
  </div>
</template>

<style>
:root {
  font-family:
    Inter,
    -apple-system,
    BlinkMacSystemFont,
    "Segoe UI",
    sans-serif;

  color: #18201e;
  background: #f4f5f1;

  font-synthesis: none;
  text-rendering: optimizeLegibility;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  min-width: 320px;
  background:
    radial-gradient(circle at 15% 0%, rgba(31, 85, 72, 0.06), transparent 30%),
    #f4f5f1;
}

a {
  color: inherit;
}

button,
input,
textarea,
select {
  font: inherit;
}

.app-shell {
  min-height: 100vh;
}

.site-header {
  height: 82px;
  padding: 0 5vw;

  display: flex;
  align-items: center;
  justify-content: space-between;

  border-bottom: 1px solid rgba(24, 32, 30, 0.1);

  background: rgba(244, 245, 241, 0.86);
  backdrop-filter: blur(16px);

  position: sticky;
  top: 0;
  z-index: 20;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-mark {
  width: 38px;
  height: 38px;

  display: grid;
  place-items: center;

  border-radius: 10px;

  background: #173f35;
  color: white;

  font-weight: 700;
  font-family: Georgia, serif;
  font-size: 21px;
}

.brand-name {
  font-size: 17px;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.brand-subtitle {
  margin-top: 2px;

  color: #7a827f;

  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.header-status {
  display: flex;
  align-items: center;
  gap: 8px;

  color: #6d7571;
  font-size: 12px;
}

.status-dot,
.available-dot {
  width: 7px;
  height: 7px;

  border-radius: 50%;

  background: #3a8d71;
  box-shadow: 0 0 0 4px rgba(58, 141, 113, 0.1);
}

.page {
  width: min(1500px, 90vw);
  margin: 0 auto;
}

.hero {
  padding: 92px 0 72px;
  max-width: 920px;
}

.eyebrow,
.section-kicker {
  color: #61716b;

  font-size: 11px;
  font-weight: 700;

  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.hero h1 {
  margin: 18px 0 22px;

  font-family: Georgia, "Times New Roman", serif;
  font-size: clamp(48px, 6vw, 86px);
  font-weight: 400;
  line-height: 0.98;
  letter-spacing: -0.045em;
}

.hero h1 span {
  color: #6f7774;
}

.hero-copy {
  max-width: 650px;
  margin: 0;

  color: #68716d;

  font-size: 17px;
  line-height: 1.65;
}

.system-message {
  padding: 28px;

  display: flex;
  align-items: center;
  gap: 18px;

  border: 1px solid #d9ddda;
  border-radius: 18px;

  background: white;
}

.system-message strong {
  font-size: 15px;
}

.system-message p {
  margin: 5px 0 0;
  color: #777f7b;
}

.system-message.error {
  border-color: #e6c5c3;
}

.loader {
  width: 28px;
  height: 28px;

  border: 3px solid #d9dfdc;
  border-top-color: #1d4b3f;
  border-radius: 50%;

  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.intelligence-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;

  border: 1px solid #d7dcd8;
  border-radius: 24px;

  background: rgba(255, 255, 255, 0.74);

  overflow: hidden;
  box-shadow: 0 18px 50px rgba(31, 46, 40, 0.06);
}

.intelligence-panel {
  min-width: 0;
  padding: 32px;
}

.investment-panel {
  border-right: 1px solid #d7dcd8;
}

.industry-panel {
  background:
    linear-gradient(
      145deg,
      rgba(235, 241, 238, 0.55),
      rgba(255, 255, 255, 0.8)
    );
}

.panel-header {
  min-height: 105px;

  display: flex;
  justify-content: space-between;
  gap: 20px;

  padding-bottom: 24px;

  border-bottom: 1px solid #e1e4e1;
}

.panel-header h2 {
  margin: 7px 0 4px;

  font-size: 28px;
  letter-spacing: -0.04em;
}

.panel-header p {
  margin: 0;

  color: #818985;
  font-size: 13px;
}

.live-pill,
.soon-pill {
  height: fit-content;

  padding: 6px 9px;

  border-radius: 100px;

  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.12em;
}

.live-pill {
  background: #e5f1eb;
  color: #277058;
}

.soon-pill {
  background: #edece7;
  color: #797970;
}

.top-signals {
  display: flex;
  flex-direction: column;
}

.signal-card {
  display: grid;
  grid-template-columns: 48px 1fr;
  gap: 18px;

  padding: 26px 0;

  border-bottom: 1px solid #e4e7e4;
}

.signal-card:last-child {
  border-bottom: 0;
}

.signal-rank {
  padding-top: 4px;

  color: #a4aaa6;

  font-family: Georgia, serif;
  font-size: 22px;
  font-style: italic;
}

.signal-content {
  min-width: 0;
}

.signal-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;

  margin-bottom: 11px;
}

.category-pill {
  color: #355e52;

  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;

  text-transform: uppercase;
}

.impact-score {
  color: #8a7251;

  font-size: 10px;
  font-weight: 700;

  letter-spacing: 0.05em;
}

.signal-card h3 {
  margin: 0;

  font-family: Georgia, "Times New Roman", serif;
  font-size: 20px;
  font-weight: 500;
  line-height: 1.3;
}

.signal-card h3 a {
  text-decoration: none;
}

.signal-card h3 a:hover {
  text-decoration: underline;
  text-decoration-thickness: 1px;
  text-underline-offset: 4px;
}

.signal-summary {
  margin: 12px 0 0;

  color: #555f5b;

  font-size: 13px;
  line-height: 1.65;
}

.impact-path {
  margin-top: 14px;
  padding: 12px 14px;

  border-left: 2px solid #78988d;

  background: #f4f7f5;

  color: #5e6864;

  font-size: 12px;
  line-height: 1.55;
}

.impact-path span {
  display: block;

  margin-bottom: 4px;

  color: #3e6156;

  font-size: 9px;
  font-weight: 700;

  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.source-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 14px;

  margin-top: 14px;

  color: #949a97;

  font-size: 10px;
}

.source-row a {
  margin-left: auto;

  color: #446a5e;

  text-decoration: none;
  font-weight: 600;
}

.industry-placeholder {
  min-height: 600px;

  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;

  padding: 60px 10%;

  text-align: center;
}

.radar-visual {
  width: 220px;
  height: 220px;

  position: relative;

  margin-bottom: 38px;
}

.radar-ring {
  position: absolute;

  border: 1px solid rgba(50, 91, 78, 0.15);
  border-radius: 50%;

  top: 50%;
  left: 50%;

  transform: translate(-50%, -50%);
}

.ring-1 {
  width: 220px;
  height: 220px;
}

.ring-2 {
  width: 150px;
  height: 150px;
}

.ring-3 {
  width: 80px;
  height: 80px;
}

.radar-center {
  width: 10px;
  height: 10px;

  position: absolute;
  top: 50%;
  left: 50%;

  transform: translate(-50%, -50%);

  border-radius: 50%;

  background: #315f51;
  box-shadow:
    0 0 0 10px rgba(49, 95, 81, 0.08),
    0 0 0 24px rgba(49, 95, 81, 0.04);
}

.placeholder-copy {
  max-width: 440px;
}

.placeholder-copy > span {
  color: #84918c;

  font-size: 9px;
  font-weight: 700;

  letter-spacing: 0.15em;
}

.placeholder-copy h3 {
  margin: 12px 0;

  font-family: Georgia, serif;
  font-size: 25px;
  font-weight: 400;
}

.placeholder-copy p {
  margin: 0;

  color: #7b8581;

  font-size: 13px;
  line-height: 1.7;
}

.empty-state {
  padding: 60px 0;
  color: #909793;
}

.explore-section {
  padding: 110px 0 90px;
}

.explore-heading {
  margin-bottom: 38px;
}

.explore-heading h2 {
  max-width: 730px;

  margin: 12px 0 0;

  font-family: Georgia, serif;
  font-size: clamp(30px, 3vw, 46px);
  font-weight: 400;
  line-height: 1.15;
  letter-spacing: -0.035em;
}

.topic-columns {
  display: grid;
  grid-template-columns: 1fr 1fr;

  border-top: 1px solid #ccd2ce;
}

.topic-column {
  min-width: 0;
  padding: 36px 34px 0 0;
}

.industry-topic-column {
  padding-right: 0;
  padding-left: 34px;

  border-left: 1px solid #ccd2ce;
}

.topic-column-heading {
  display: flex;
  align-items: flex-start;
  gap: 16px;

  margin-bottom: 28px;
}

.column-number {
  color: #a2a9a5;

  font-family: Georgia, serif;
  font-size: 18px;
  font-style: italic;
}

.topic-column-heading h3 {
  margin: 5px 0 0;

  font-size: 22px;
  letter-spacing: -0.025em;
}

.topic-list {
  display: grid;
  gap: 12px;
}

.topic-card {
  padding: 22px 22px 20px;

  border: 1px solid #d8ddda;
  border-radius: 16px;

  background: rgba(255, 255, 255, 0.7);

  transition:
    transform 0.2s ease,
    border-color 0.2s ease,
    box-shadow 0.2s ease;
}

.topic-card:hover {
  transform: translateY(-2px);

  border-color: #bdc8c3;

  box-shadow: 0 12px 30px rgba(30, 45, 40, 0.05);
}

.industry-topic-card {
  background: rgba(237, 241, 238, 0.6);
}

.topic-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.topic-card h4 {
  margin: 0;

  font-family: Georgia, serif;
  font-size: 18px;
  font-weight: 500;
}

.topic-card-header div > span {
  display: block;

  margin-top: 3px;

  color: #929996;

  font-size: 11px;
}

.coming-tag {
  white-space: nowrap;

  padding: 5px 7px;

  border-radius: 6px;

  background: #ecece7;
  color: #888a82;

  font-size: 8px;
  font-weight: 700;

  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.topic-description {
  margin: 15px 0 0;

  color: #6d7773;

  font-size: 12px;
  line-height: 1.55;
}

.topic-story {
  margin-top: 19px;
  padding-top: 16px;

  border-top: 1px solid #e3e6e3;
}

.topic-story > span {
  display: block;

  margin-bottom: 7px;

  color: #87918d;

  font-size: 8px;
  font-weight: 700;

  letter-spacing: 0.12em;
}

.topic-story a {
  color: #2b4d43;

  font-size: 12px;
  font-weight: 600;
  line-height: 1.5;

  text-decoration: none;
}

.topic-story a:hover {
  text-decoration: underline;
}

.topic-empty {
  margin-top: 18px;
  padding-top: 15px;

  border-top: 1px solid #e3e6e3;

  color: #a0a6a3;

  font-size: 10px;
}

footer {
  width: min(1500px, 90vw);

  margin: 0 auto;
  padding: 36px 0 60px;

  border-top: 1px solid #d2d7d3;
}

footer p {
  max-width: 440px;

  margin: 8px 0 0;

  color: #8c9490;

  font-size: 11px;
  line-height: 1.6;
}

@media (max-width: 1000px) {
  .intelligence-grid,
  .topic-columns {
    grid-template-columns: 1fr;
  }

  .investment-panel {
    border-right: 0;
    border-bottom: 1px solid #d7dcd8;
  }

  .industry-topic-column {
    padding-left: 0;
    border-left: 0;
    border-top: 1px solid #ccd2ce;

    margin-top: 45px;
    padding-top: 36px;
  }

  .topic-column {
    padding-right: 0;
  }

  .industry-placeholder {
    min-height: 450px;
  }
}

@media (max-width: 640px) {
  .site-header {
    height: 70px;
  }

  .brand-subtitle {
    display: none;
  }

  .header-status {
    font-size: 10px;
  }

  .page {
    width: 92vw;
  }

  .hero {
    padding: 65px 0 50px;
  }

  .hero h1 {
    font-size: 46px;
  }

  .hero-copy {
    font-size: 14px;
  }

  .intelligence-panel {
    padding: 22px;
  }

  .panel-header {
    flex-direction: column;
  }

  .signal-card {
    grid-template-columns: 35px 1fr;
    gap: 10px;
  }

  .signal-meta {
    align-items: flex-start;
    gap: 10px;
  }

  .source-row a {
    width: 100%;
    margin-left: 0;
  }

  .industry-placeholder {
    padding: 50px 0;
  }

  .radar-visual {
    width: 160px;
    height: 160px;
  }

  .ring-1 {
    width: 160px;
    height: 160px;
  }

  .ring-2 {
    width: 110px;
    height: 110px;
  }

  .ring-3 {
    width: 60px;
    height: 60px;
  }

  .explore-section {
    padding: 75px 0;
  }
}
</style>