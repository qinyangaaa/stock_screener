import { useEffect, useState, useCallback } from "react";
import { Empty, Spin, Typography, Divider } from "antd";
import type { Recommendation, RunStatus } from "../types/stock";
import { fetchLatest } from "../services/api";
import StockCard from "./StockCard";
import StockDetail from "./StockDetail";
import TriggerPanel from "./TriggerPanel";

const { Title } = Typography;

export default function Dashboard() {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<{
    date: string | null;
    recommendations: Recommendation[];
    last_run: RunStatus | null;
    is_trading_day: boolean;
  } | null>(null);
  const [selectedStock, setSelectedStock] = useState<Recommendation | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const result = await fetchLatest();
      setData(result);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div>
      <TriggerPanel
        lastRun={data?.last_run ?? null}
        isTradingDay={data?.is_trading_day ?? true}
        onRefresh={load}
      />

      <Divider />

      <Title level={4} style={{ marginTop: 0 }}>
        {data?.date ? `推荐结果 (${data.date})` : "暂无推荐结果"}
        {data?.total ? <span style={{ fontSize: 14, color: "#999", marginLeft: 12 }}>共 {data.total} 只</span> : null}
      </Title>

      {loading ? (
        <div style={{ textAlign: "center", padding: 48 }}>
          <Spin size="large" />
        </div>
      ) : !data?.recommendations?.length ? (
        <Empty description="暂无推荐数据，请手动触发筛选或等待 14:30 自动运行" />
      ) : (
        data.recommendations.map((stock) => (
          <StockCard
            key={stock.id}
            stock={stock}
            onClick={() => setSelectedStock(stock)}
          />
        ))
      )}

      <StockDetail
        stock={selectedStock}
        onClose={() => setSelectedStock(null)}
      />
    </div>
  );
}
