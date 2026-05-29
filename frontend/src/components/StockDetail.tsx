import { useEffect, useState } from "react";
import {
  Drawer, Descriptions, Table, Tag, Typography, Spin, Card, Statistic, Row, Col,
} from "antd";
import {
  CheckCircleOutlined, CloseCircleOutlined, CaretUpOutlined,
} from "@ant-design/icons";
import type { Recommendation, Stage2CandidateResult } from "../types/stock";
import { fetchStockDetail } from "../services/api";

const { Text, Title } = Typography;

interface Props {
  stock: Recommendation | null;
  onClose: () => void;
}

const RULE_NAME_MAP: Record<string, string> = {
  stage1: "第一级过滤 (规则1-4)",
  rule5: "规则5: 台阶式放量",
  rule6: "规则6: 多头排列+套牢盘",
  rule7: "规则7: 分时强度",
  rule8: "规则8: 尾盘信号",
};

export default function StockDetail({ stock, onClose }: Props) {
  const [analysis, setAnalysis] = useState<Stage2CandidateResult | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!stock) {
      setAnalysis(null);
      return;
    }
    setLoading(true);
    fetchStockDetail(stock.code)
      .then((res) => {
        if (res.analysis) setAnalysis(res.analysis);
      })
      .catch(() => setAnalysis(null))
      .finally(() => setLoading(false));
  }, [stock?.code]);

  if (!stock) return null;

  const ruleColumns = [
    { title: "规则", dataIndex: "rule", key: "rule", width: 180 },
    {
      title: "结果",
      dataIndex: "passed",
      key: "passed",
      width: 80,
      render: (v: boolean) =>
        v ? (
          <Tag icon={<CheckCircleOutlined />} color="success">通过</Tag>
        ) : (
          <Tag icon={<CloseCircleOutlined />} color="error">未通过</Tag>
        ),
    },
    { title: "详情", dataIndex: "detail", key: "detail" },
  ];

  // 构建规则明细数据
  const ruleDetails = stock.rule_details || {};
  const ruleData: { key: string; rule: string; passed: boolean; detail: string }[] = [];

  const allRuleKeys = ["rule5", "rule6", "rule7", "rule8"];
  for (const rk of allRuleKeys) {
    const fromStock = ruleDetails[rk] as { passed: boolean; detail: string } | undefined;
    const fromAnalysis = analysis?.rule_results?.[rk];
    const best = fromStock && fromStock.detail ? fromStock : fromAnalysis;
    ruleData.push({
      key: rk,
      rule: RULE_NAME_MAP[rk] || rk,
      passed: best?.passed ?? false,
      detail: best?.detail ?? "-",
    });
  }

  return (
    <Drawer
      title={`${stock.name} (${stock.code}) 详细分析`}
      open
      onClose={onClose}
      width={680}
    >
      {/* 基本评分信息 */}
      <Descriptions column={3} bordered size="small" style={{ marginBottom: 16 }}>
        <Descriptions.Item label="排名">
          <Text strong>#{stock.rank}</Text>
        </Descriptions.Item>
        <Descriptions.Item label="综合评分">
          <Text strong style={{ color: "#cf1322", fontSize: 16 }}>{stock.score} 分</Text>
        </Descriptions.Item>
        <Descriptions.Item label="信号">
          <Tag color={stock.signal === "strong_buy" ? "red" : stock.signal === "buy" ? "orange" : "default"}>
            {stock.signal === "strong_buy" ? "强烈推荐" : stock.signal === "buy" ? "建议关注" : "观望"}
          </Tag>
        </Descriptions.Item>
      </Descriptions>

      {/* 关键指标 */}
      <Row gutter={12} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="涨跌幅"
              value={stock.change_pct}
              suffix="%"
              precision={2}
              valueStyle={{ color: stock.change_pct >= 0 ? "#cf1322" : "#3f8600", fontSize: 18 }}
              prefix={<CaretUpOutlined rotate={stock.change_pct < 0 ? 180 : 0} />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic title="量比" value={stock.volume_ratio?.toFixed(2)} valueStyle={{ fontSize: 18 }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic title="换手率" value={stock.turnover} suffix="%" valueStyle={{ fontSize: 18 }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="流通市值"
              value={stock.market_cap > 0 ? stock.market_cap.toFixed(0) : "-"}
              suffix={stock.market_cap > 0 ? "亿" : ""}
              valueStyle={{ fontSize: 18 }}
            />
          </Card>
        </Col>
      </Row>

      {/* 筛选详情 */}
      {loading ? (
        <Spin style={{ display: "block", margin: "20px auto" }} />
      ) : (
        <>
          <Text type="secondary" style={{ marginBottom: 4, display: "block" }}>
            筛选日期: {stock.screening_date}
          </Text>

          <Title level={5} style={{ marginTop: 16 }}>
            各规则通过详情
          </Title>
          <Table
            dataSource={ruleData}
            columns={ruleColumns}
            pagination={false}
            size="small"
            locale={{ emptyText: "暂无规则详情" }}
          />

          {analysis && (
            <Card size="small" title="当前筛选指标" style={{ marginTop: 16 }}>
              <Descriptions column={2} size="small">
                <Descriptions.Item label="涨跌幅">{analysis.change_pct}%</Descriptions.Item>
                <Descriptions.Item label="量比">{analysis.volume_ratio?.toFixed(2) || "-"}</Descriptions.Item>
                <Descriptions.Item label="换手率">{analysis.turnover}%</Descriptions.Item>
                <Descriptions.Item label="流通市值">{analysis.market_cap > 0 ? `${analysis.market_cap.toFixed(0)}亿` : "-"}</Descriptions.Item>
              </Descriptions>
            </Card>
          )}
        </>
      )}
    </Drawer>
  );
}
