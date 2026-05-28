import { Drawer, Descriptions, Table, Tag, Typography } from "antd";
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  CaretUpOutlined,
} from "@ant-design/icons";
import type { Recommendation } from "../types/stock";

const { Text } = Typography;

interface Props {
  stock: Recommendation | null;
  onClose: () => void;
}

export default function StockDetail({ stock, onClose }: Props) {
  if (!stock) return null;

  const ruleColumns = [
    { title: "规则", dataIndex: "rule", key: "rule", width: 160 },
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

  const ruleData = Object.entries(stock.rule_details || {}).map(([key, val]) => ({
    key,
    rule: key === "stage1" ? "第一级过滤" : key,
    passed: val.passed ?? true,
    detail: val.detail ?? "",
  }));

  return (
    <Drawer
      title={`${stock.name} (${stock.code}) 详细分析`}
      open
      onClose={onClose}
      width={640}
    >
      <Descriptions column={2} bordered size="small" style={{ marginBottom: 24 }}>
        <Descriptions.Item label="排名">
          <Text strong>#{stock.rank}</Text>
        </Descriptions.Item>
        <Descriptions.Item label="评分">
          <Text strong style={{ color: "#cf1322", fontSize: 16 }}>
            {stock.score} 分
          </Text>
        </Descriptions.Item>
        <Descriptions.Item label="信号">
          {stock.signal === "strong_buy"
            ? "强烈推荐"
            : stock.signal === "buy"
              ? "建议关注"
              : "观望"}
        </Descriptions.Item>
        <Descriptions.Item label="涨幅">
          <Text style={{ color: stock.change_pct > 0 ? "#cf1322" : "#52c41a" }}>
            <CaretUpOutlined rotate={stock.change_pct < 0 ? 180 : 0} />
            {stock.change_pct}%
          </Text>
        </Descriptions.Item>
        <Descriptions.Item label="量比">
          {stock.volume_ratio.toFixed(2)}
        </Descriptions.Item>
        <Descriptions.Item label="换手率">
          {stock.turnover}%
        </Descriptions.Item>
        <Descriptions.Item label="流通市值">
          {stock.market_cap.toFixed(0)}亿
        </Descriptions.Item>
        <Descriptions.Item label="筛选日期">
          {stock.screening_date}
        </Descriptions.Item>
      </Descriptions>

      <Text strong style={{ marginBottom: 8, display: "block" }}>
        规则通过情况
      </Text>
      <Table
        dataSource={ruleData}
        columns={ruleColumns}
        pagination={false}
        size="small"
      />
    </Drawer>
  );
}
