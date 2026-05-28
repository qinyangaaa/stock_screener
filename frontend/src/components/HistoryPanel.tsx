import { useEffect, useState, useCallback } from "react";
import { List, Card, Select, Empty, Spin, Tag, Typography } from "antd";
import { CalendarOutlined } from "@ant-design/icons";
import type { Recommendation } from "../types/stock";
import { fetchHistory, fetchHistoryDates } from "../services/api";
import StatusBadge from "./StatusBadge";
import StockDetail from "./StockDetail";

const { Text } = Typography;

export default function HistoryPanel() {
  const [dates, setDates] = useState<string[]>([]);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [stocks, setStocks] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedStock, setSelectedStock] = useState<Recommendation | null>(null);

  const loadDates = useCallback(async () => {
    try {
      const data = await fetchHistoryDates();
      setDates(data.dates);
      if (data.dates.length > 0) {
        setSelectedDate(data.dates[0]);
      }
    } catch {
      // ignore
    }
  }, []);

  const loadHistory = useCallback(async (date: string) => {
    setLoading(true);
    try {
      const data = await fetchHistory(date);
      setStocks(data.recommendations);
    } catch {
      setStocks([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDates();
  }, [loadDates]);

  useEffect(() => {
    if (selectedDate) {
      loadHistory(selectedDate);
    }
  }, [selectedDate, loadHistory]);

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Text strong>
          <CalendarOutlined /> 选择日期:
        </Text>
        <Select
          style={{ width: 200, marginLeft: 12 }}
          value={selectedDate}
          onChange={setSelectedDate}
          loading={dates.length === 0}
          options={dates.map((d) => ({ label: d, value: d }))}
          placeholder="选择筛选日期"
        />
        {selectedDate && (
          <Text type="secondary" style={{ marginLeft: 12 }}>
            共 {stocks.length} 只推荐
          </Text>
        )}
      </div>

      {loading ? (
        <div style={{ textAlign: "center", padding: 48 }}>
          <Spin size="large" />
        </div>
      ) : !selectedDate || stocks.length === 0 ? (
        <Empty description="该日期无推荐记录" />
      ) : (
        <List
          dataSource={stocks}
          renderItem={(stock) => (
            <List.Item
              onClick={() => setSelectedStock(stock)}
              style={{ cursor: "pointer" }}
            >
              <Card hoverable style={{ width: "100%" }}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <div>
                    <StatusBadge signal={stock.signal} />
                    <Text strong style={{ fontSize: 16, marginLeft: 8 }}>
                      #{stock.rank} {stock.name}
                    </Text>
                    <Text type="secondary" style={{ marginLeft: 8 }}>
                      {stock.code}
                    </Text>
                  </div>
                  <div>
                    <Text strong style={{ fontSize: 18, color: "#cf1322" }}>
                      {stock.score} 分
                    </Text>
                    <Tag style={{ marginLeft: 8 }}>
                      量比: {stock.volume_ratio.toFixed(2)}
                    </Tag>
                    <Tag>
                      涨幅: {stock.change_pct}%
                    </Tag>
                    <Tag>
                      换手: {stock.turnover}%
                    </Tag>
                  </div>
                </div>
              </Card>
            </List.Item>
          )}
        />
      )}

      <StockDetail
        stock={selectedStock}
        onClose={() => setSelectedStock(null)}
      />
    </div>
  );
}
