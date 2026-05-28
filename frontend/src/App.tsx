import { ConfigProvider, Layout, Tabs, theme } from "antd";
import { LineChartOutlined, HistoryOutlined, FilterOutlined } from "@ant-design/icons";
import zhCN from "antd/locale/zh_CN";
import { useState } from "react";
import Dashboard from "./components/Dashboard";
import HistoryPanel from "./components/HistoryPanel";
import BreakdownPanel from "./components/BreakdownPanel";

const { Header, Content } = Layout;

export default function App() {
  const [activeTab, setActiveTab] = useState("today");

  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        algorithm: theme.defaultAlgorithm,
        token: { colorPrimary: "#cf1322" },
      }}
    >
      <Layout style={{ minHeight: "100vh" }}>
        <Header
          style={{
            display: "flex",
            alignItems: "center",
            background: "#cf1322",
            padding: "0 24px",
          }}
        >
          <h1 style={{ color: "#fff", margin: 0, fontSize: 20, fontWeight: 600 }}>
            股票推荐小工具
          </h1>
        </Header>
        <Content style={{ padding: "24px", maxWidth: 1200, margin: "0 auto", width: "100%" }}>
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            size="large"
            items={[
              {
                key: "today",
                label: (
                  <span>
                    <LineChartOutlined />
                    今日推荐
                  </span>
                ),
                children: <Dashboard />,
              },
              {
                key: "breakdown",
                label: (
                  <span>
                    <FilterOutlined />
                    筛选明细
                  </span>
                ),
                children: <BreakdownPanel />,
              },
              {
                key: "history",
                label: (
                  <span>
                    <HistoryOutlined />
                    历史记录
                  </span>
                ),
                children: <HistoryPanel />,
              },
            ]}
          />
        </Content>
      </Layout>
    </ConfigProvider>
  );
}
