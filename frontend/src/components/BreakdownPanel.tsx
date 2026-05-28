import { useEffect, useState } from "react";
import {
  Card, Col, Row, Statistic, Table, Tag, Typography, Collapse, Empty, Spin, Alert,
} from "antd";
import {
  FilterOutlined, CheckCircleOutlined, CloseCircleOutlined,
  WarningOutlined, FallOutlined,
} from "@ant-design/icons";
import type { ScreeningDetails, Stage2FailedResult, Stage1FailedSample } from "../types/stock";
import { fetchScreeningDetails } from "../services/api";

const { Title, Text } = Typography;

const RULE_LABELS_S1: Record<string, string> = {
  rule1_change_pct: "规则1: 涨幅",
  rule2_volume_ratio: "规则2: 量比",
  rule3_turnover: "规则3: 换手率",
  rule4_market_cap: "规则4: 流通市值",
};

const RULE_LABELS_S2: Record<string, string> = {
  no_data: "数据不足 (分钟K线 < 6)",
  rule5: "规则5: 台阶式放量",
  rule6: "规则6: 多头排列+套牢盘",
  rule7: "规则7: 分时强度",
  rule8: "规则8: 尾盘信号",
};

function getSampleValueCol(ruleKey: string) {
  const map: Record<string, { key: string; label: string; suffix: string }> = {
    rule1_change_pct: { key: "change_pct", label: "涨跌幅", suffix: "%" },
    rule2_volume_ratio: { key: "volume_ratio", label: "量比", suffix: "" },
    rule3_turnover: { key: "turnover", label: "换手率", suffix: "%" },
    rule4_market_cap: { key: "market_cap", label: "流通市值", suffix: "亿" },
  };
  return map[ruleKey] || { key: "detail", label: "原因", suffix: "" };
}

export default function BreakdownPanel() {
  const [details, setDetails] = useState<ScreeningDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchScreeningDetails();
      setDetails(res.details);
    } catch {
      setError("暂无筛选明细数据，请先运行一次筛选");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  if (loading) return <Spin size="large" style={{ display: "block", margin: "60px auto" }} />;
  if (error) return <Alert type="info" message={error} showIcon action={<a onClick={load}>刷新</a>} />;
  if (!details || !details.total_stocks) return <Empty description="暂无筛选数据" />;

  const { stage1, stage2 } = details;

  // ==== Stage 1 failed samples table ====
  const stage1SampleTables = Object.entries(stage1.failed_samples).map(([ruleKey, samples]) => {
    const { key, label, suffix } = getSampleValueCol(ruleKey);
    const columns = [
      { title: "代码", dataIndex: "code", key: "code", width: 90 },
      { title: "名称", dataIndex: "name", key: "name", width: 100 },
      {
        title: label,
        dataIndex: key,
        key,
        width: 120,
        render: (v: number) => v !== undefined ? `${v}${suffix}` : "-",
      },
      { title: "判定", dataIndex: "detail", key: "detail", ellipsis: true },
    ];
    return (
      <Card
        key={ruleKey}
        size="small"
        title={
          <span>
            {RULE_LABELS_S1[ruleKey] || ruleKey}
            <Tag color="red" style={{ marginLeft: 8 }}>{samples.length} 只样本</Tag>
          </span>
        }
        style={{ marginBottom: 12 }}
      >
        <Table
          dataSource={samples}
          columns={columns}
          rowKey="code"
          size="small"
          pagination={false}
        />
      </Card>
    );
  });

  // ==== Stage 2 candidates table ====
  const stage2CandidateCols = [
    { title: "代码", dataIndex: "code", key: "code", width: 90 },
    { title: "名称", dataIndex: "name", key: "name", width: 100 },
    {
      title: "涨跌幅", dataIndex: "change_pct", key: "change_pct", width: 80,
      render: (v: number) => (
        <span style={{ color: v >= 0 ? "#cf1322" : "#3f8600" }}>{v}%</span>
      ),
    },
    { title: "量比", dataIndex: "volume_ratio", key: "volume_ratio", width: 70 },
    { title: "换手率", dataIndex: "turnover", key: "turnover", width: 80, render: (v: number) => `${v}%` },
    { title: "市值(亿)", dataIndex: "market_cap", key: "market_cap", width: 90 },
    {
      title: "规则5", dataIndex: ["rule_results", "rule5", "passed"], key: "r5", width: 70,
      render: (v: boolean | undefined) => v === true
        ? <CheckCircleOutlined style={{ color: "#52c41a" }} />
        : v === false ? <CloseCircleOutlined style={{ color: "#ff4d4f" }} /> : "-",
    },
    {
      title: "规则6", dataIndex: ["rule_results", "rule6", "passed"], key: "r6", width: 70,
      render: (v: boolean | undefined) => v === true
        ? <CheckCircleOutlined style={{ color: "#52c41a" }} />
        : v === false ? <CloseCircleOutlined style={{ color: "#ff4d4f" }} /> : "-",
    },
    {
      title: "规则7", dataIndex: ["rule_results", "rule7", "passed"], key: "r7", width: 70,
      render: (v: boolean | undefined) => v === true
        ? <CheckCircleOutlined style={{ color: "#52c41a" }} />
        : v === false ? <CloseCircleOutlined style={{ color: "#ff4d4f" }} /> : "-",
    },
    {
      title: "规则8", dataIndex: ["rule_results", "rule8", "passed"], key: "r8", width: 70,
      render: (v: boolean | undefined) => v === true
        ? <CheckCircleOutlined style={{ color: "#52c41a" }} />
        : v === false ? <CloseCircleOutlined style={{ color: "#ff4d4f" }} /> : "-",
    },
  ];

  // ==== Stage 2 failed table ====
  const stage2FailedCols = [
    { title: "代码", dataIndex: "code", key: "code", width: 90 },
    { title: "名称", dataIndex: "name", key: "name", width: 100 },
    {
      title: "涨跌幅", dataIndex: "change_pct", key: "change_pct", width: 80,
      render: (v: number) => (
        <span style={{ color: v >= 0 ? "#cf1322" : "#3f8600" }}>{v}%</span>
      ),
    },
    { title: "量比", dataIndex: "volume_ratio", key: "volume_ratio", width: 70 },
    { title: "换手率", dataIndex: "turnover", key: "turnover", width: 80, render: (v: number) => `${v}%` },
    { title: "市值(亿)", dataIndex: "market_cap", key: "market_cap", width: 90 },
    {
      title: "失败于",
      dataIndex: "failed_rule",
      key: "failed_rule",
      width: 180,
      render: (v: string) => <Tag color="error">{RULE_LABELS_S2[v] || v}</Tag>,
    },
    {
      title: "已通过规则", key: "passed_rules", ellipsis: true,
      render: (_: unknown, r: Stage2FailedResult) => {
        const passed = Object.entries(r.rule_results)
          .filter(([, v]) => v.passed)
          .map(([k]) => k.replace("rule", "R"));
        return passed.length ? passed.join(", ") : "-";
      },
    },
  ];

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const stage2CandidatesAll: any[] = [
    ...(stage2.candidates || []).map((c) => ({ ...c, _type: "passed" })),
    ...(stage2.failed || []).map((c) => ({ ...c, _type: "failed" })),
  ];

  return (
    <div>
      {/* ======== 概览漏斗 ======== */}
      <Card style={{ marginBottom: 16 }}>
        <Title level={5} style={{ marginTop: 0 }}>
          <FilterOutlined /> 筛选漏斗概览
          {stage1.is_extreme && (
            <Tag color="orange" style={{ marginLeft: 8 }}>
              <WarningOutlined /> 极端行情（放宽涨幅阈值）
            </Tag>
          )}
        </Title>
        <Row gutter={16}>
          <Col span={6}>
            <Statistic title="全市场" value={details.total_stocks} suffix="只" />
          </Col>
          <Col span={6}>
            <Statistic
              title="一级过滤通过"
              value={stage1.passed}
              suffix={`只 (${details.total_stocks > 0 ? (stage1.passed / details.total_stocks * 100).toFixed(1) : 0}%)`}
              valueStyle={{ color: "#1890ff" }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="二级过滤通过"
              value={stage2.passed}
              suffix={`只 (${stage1.passed > 0 ? (stage2.passed / stage1.passed * 100).toFixed(1) : 0}%)`}
              valueStyle={{ color: stage2.passed > 0 ? "#52c41a" : "#ff4d4f" }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="最终推荐"
              value={stage2.passed}
              suffix="只"
              valueStyle={{ color: stage2.passed >= 3 ? "#cf1322" : "#faad14" }}
            />
          </Col>
        </Row>
      </Card>

      {/* ======== 一级过滤明细 ======== */}
      <Collapse
        size="small"
        style={{ marginBottom: 16 }}
        items={[{
          key: "stage1",
          label: (
            <span>
              <FallOutlined /> 第一级过滤明细 — 全市场 {details.total_stocks} 只 → 通过 {stage1.passed} 只
            </span>
          ),
          children: (
            <div>
              <Row gutter={16} style={{ marginBottom: 16 }}>
                {Object.entries(RULE_LABELS_S1).map(([key, label]) => (
                  <Col span={6} key={key}>
                    <Card size="small">
                      <Statistic
                        title={label}
                        value={stage1.rule_fails[key] || 0}
                        suffix={`只未通过 (${details.total_stocks > 0
                          ? ((stage1.rule_fails[key] || 0) / details.total_stocks * 100).toFixed(1)
                          : 0}%)`}
                        valueStyle={{ color: "#ff4d4f", fontSize: 20 }}
                      />
                    </Card>
                  </Col>
                ))}
              </Row>
              <Text type="secondary">
                以下展示各规则未通过的前30只样本，可了解具体哪些指标不达标。
              </Text>
              {stage1SampleTables.length > 0 ? stage1SampleTables : (
                <Empty description="所有规则一级过滤全部通过（非常罕见）" />
              )}
            </div>
          ),
        }]}
      />

      {/* ======== 二级过滤明细 ======== */}
      <Collapse
        size="small"
        style={{ marginBottom: 16 }}
        items={[
          {
            key: "stage2_overview",
            label: (
              <span>
                <FallOutlined /> 第二级过滤明细 — 进入 {stage1.passed} 只 → 通过 {stage2.passed} 只
              </span>
            ),
            children: (
              <div>
                <Row gutter={16} style={{ marginBottom: 16 }}>
                  {Object.entries(RULE_LABELS_S2).map(([key, label]) => {
                    const count = stage2.rule_fails[key] || 0;
                    return (
                      <Col span={Math.floor(24 / Object.keys(RULE_LABELS_S2).length)} key={key}>
                        <Card size="small">
                          <Statistic
                            title={label}
                            value={count}
                            suffix="只"
                            valueStyle={{ color: count === 0 ? "#52c41a" : "#ff4d4f", fontSize: 18 }}
                          />
                        </Card>
                      </Col>
                    );
                  })}
                </Row>

                <Title level={5} style={{ marginTop: 16 }}>
                  候选股规则通过矩阵（共 {stage2CandidatesAll.length} 只）
                </Title>
                <Table
                  dataSource={stage2CandidatesAll}
                  columns={stage2CandidateCols}
                  rowKey={(r) => r.code + r._type}
                  size="small"
                  pagination={{ pageSize: 50, size: "small" }}
                  scroll={{ x: 800 }}
                  locale={{ emptyText: "无候选股进入二级过滤" }}
                />

                {stage2.failed && stage2.failed.length > 0 && (
                  <>
                    <Title level={5} style={{ marginTop: 16, color: "#ff4d4f" }}>
                      被淘汰的候选股（共 {stage2.failed.length} 只）
                    </Title>
                    <Table
                      dataSource={stage2.failed}
                      columns={stage2FailedCols}
                      rowKey="code"
                      size="small"
                      pagination={{ pageSize: 50, size: "small" }}
                      scroll={{ x: 800 }}
                    />
                  </>
                )}
              </div>
            ),
          },
        ]}
      />
    </div>
  );
}
