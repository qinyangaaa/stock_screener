import { Card, Descriptions, Space, Typography } from "antd";
import { CaretUpOutlined } from "@ant-design/icons";
import type { Recommendation } from "../types/stock";
import StatusBadge from "./StatusBadge";

const { Text } = Typography;

interface Props {
  stock: Recommendation;
  onClick?: () => void;
}

export default function StockCard({ stock, onClick }: Props) {
  return (
    <Card
      hoverable
      onClick={onClick}
      style={{ marginBottom: 12 }}
      title={
        <Space>
          <StatusBadge signal={stock.signal} />
          <Text strong style={{ fontSize: 16 }}>
            #{stock.rank} {stock.name}
          </Text>
          <Text type="secondary">{stock.code}</Text>
        </Space>
      }
      extra={
        <Text strong style={{ fontSize: 18, color: "#cf1322" }}>
          {stock.score} 分
        </Text>
      }
    >
      <Descriptions size="small" column={4}>
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
      </Descriptions>
    </Card>
  );
}
