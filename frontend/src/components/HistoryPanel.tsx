import { useEffect, useState, useCallback } from "react";
import {
  Tabs, Table, Card, Empty, Spin, Tag, Typography, Descriptions,
} from "antd";
import { HistoryOutlined, ClockCircleOutlined } from "@ant-design/icons";
import type { Recommendation, RunStatus } from "../types/stock";
import { fetchHistoryDates, fetchHistory, fetchScreeningRuns } from "../services/api";
import StatusBadge from "./StatusBadge";
import StockDetail from "./StockDetail";

const { Text, Title } = Typography;

export default function HistoryPanel() {
  const [dates, setDates] = useState<string[]>([]);
  const [runs, setRuns] = useState<RunStatus[]>([]);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [stocks, setStocks] = useState<Recommendation[]>([]);
  const [loadingStocks, setLoadingStocks] = useState(false);
  const [loadingRuns, setLoadingRuns] = useState(true);
  const [selectedStock, setSelectedStock] = useState<Recommendation | null>(null);

  const loadData = useCallback(async () => {
    setLoadingRuns(true);
    try {
      const [datesData, runsData] = await Promise.all([
        fetchHistoryDates(),
        fetchScreeningRuns(),
      ]);
      setDates(datesData.dates);
      setRuns(runsData.runs || []);
      if (datesData.dates.length > 0) {
        setSelectedDate((prev) => prev || datesData.dates[0]);
      }
    } catch {
      // ignore
    } finally {
      setLoadingRuns(false);
    }
  }, []);

  const loadHistory = useCallback(async (date: string) => {
    setLoadingStocks(true);
    try {
      const data = await fetchHistory(date);
      setStocks(data.recommendations || []);
    } catch {
      setStocks([]);
    } finally {
      setLoadingStocks(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  useEffect(() => {
    if (selectedDate) loadHistory(selectedDate);
  }, [selectedDate, loadHistory]);

  const runColumns = [
    { title: "日期", dataIndex: "started_at", key: "started_at", width: 180,
      render: (v: string) => v?.slice(0, 16) },
    {
      title: "状态", dataIndex: "status", key: "status", width: 90,
      render: (v: string) => {
        const map: Record<string, { color: string; text: string }> = {
          completed: { color: "green", text: "完成" },
          running: { color: "blue", text: "运行中" },
          failed: { color: "red", text: "失败" },
        };
        const info = map[v] || { color: "default", text: v };
        return <Tag color={info.color}>{info.text}</Tag>;
      },
    },
    { title: "全市场", dataIndex: "total_stocks", key: "total_stocks", width: 80 },
    { title: "一级通过", dataIndex: "passed_stage1", key: "passed_stage1", width: 80 },
    { title: "最终推荐", dataIndex: "passed_all", key: "passed_all", width: 80,
      render: (v: number) => <Text strong style={{ color: v > 0 ? "#cf1322" : "#999" }}>{v}</Text> },
    { title: "错误信息", dataIndex: "error", key: "error", ellipsis: true },
  ];

  const runDates = runs.map((r) => r.started_at?.slice(0, 10) || "").filter(Boolean);

  return (
    <div>
      <Title level={5}>
        <HistoryOutlined /> 历史记录
      </Title>

      <Tabs
        size="small"
        items={[
          {
            key: "runs",
            label: <span><ClockCircleOutlined /> 运行日志（{runs.length} 次）</span>,
            children: (
              <div>
                {loadingRuns ? (
                  <Spin size="large" style={{ display: "block", margin: "40px auto" }} />
                ) : runs.length === 0 ? (
                  <Empty description="暂无运行记录" />
                ) : (
                  <Table
                    dataSource={runs}
                    columns={runColumns}
                    rowKey="id"
                    size="small"
                    pagination={{ pageSize: 20, size: "small" }}
                    expandable={{
                      expandedRowRender: (run: RunStatus) => (
                        <Descriptions size="small" column={2} bordered>
                          <Descriptions.Item label="任务 ID">{run.task_id}</Descriptions.Item>
                          <Descriptions.Item label="状态">{run.status}</Descriptions.Item>
                          <Descriptions.Item label="开始时间">{run.started_at}</Descriptions.Item>
                          <Descriptions.Item label="结束时间">{run.finished_at || "-"}</Descriptions.Item>
                          <Descriptions.Item label="全市场股票">{run.total_stocks}</Descriptions.Item>
                          <Descriptions.Item label="一级通过">{run.passed_stage1}</Descriptions.Item>
                          <Descriptions.Item label="最终通过">{run.passed_all}</Descriptions.Item>
                          <Descriptions.Item label="错误">{run.error || "无"}</Descriptions.Item>
                        </Descriptions>
                      ),
                    }}
                  />
                )}
              </div>
            ),
          },
          {
            key: "recommendations",
            label: <span>推荐记录（{dates.length} 天）</span>,
            children: (
              <div>
                <div style={{ marginBottom: 12 }}>
                  <Text type="secondary">
                    {dates.length > 0
                      ? `共有 ${dates.length} 个交易日有推荐记录`
                      : "暂无推荐记录 — 当筛选通过股数 > 0 时才会保存"}
                  </Text>
                  {dates.length > 0 && (
                    <div style={{ marginTop: 8 }}>
                      {dates.map((d) => (
                        <Tag
                          key={d}
                          color={d === selectedDate ? "blue" : "default"}
                          style={{ cursor: "pointer", marginBottom: 4 }}
                          onClick={() => setSelectedDate(d)}
                        >
                          {d}
                        </Tag>
                      ))}
                    </div>
                  )}
                </div>

                {loadingStocks ? (
                  <Spin style={{ display: "block", margin: "40px auto" }} />
                ) : !selectedDate ? (
                  <Empty description="选择日期查看推荐" />
                ) : stocks.length === 0 ? (
                  <Empty description={`${selectedDate} 无推荐记录`} />
                ) : (
                  <>
                    <Text type="secondary" style={{ marginBottom: 8, display: "block" }}>
                      {selectedDate} — 共 {stocks.length} 只推荐
                    </Text>
                    {stocks.map((stock) => (
                      <Card
                        key={stock.id}
                        hoverable
                        size="small"
                        style={{ marginBottom: 8 }}
                        onClick={() => setSelectedStock(stock)}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                          <div>
                            <StatusBadge signal={stock.signal} />
                            <Text strong style={{ fontSize: 15, marginLeft: 8 }}>
                              #{stock.rank} {stock.name}
                            </Text>
                            <Text type="secondary" style={{ marginLeft: 8 }}>{stock.code}</Text>
                          </div>
                          <div>
                            <Text strong style={{ fontSize: 16, color: "#cf1322" }}>{stock.score} 分</Text>
                            <Tag style={{ marginLeft: 8 }}>量比: {stock.volume_ratio?.toFixed(2)}</Tag>
                            <Tag>涨幅: {stock.change_pct}%</Tag>
                            <Tag>换手: {stock.turnover}%</Tag>
                          </div>
                        </div>
                      </Card>
                    ))}
                  </>
                )}
              </div>
            ),
          },
        ]}
      />

      <StockDetail
        stock={selectedStock}
        onClose={() => setSelectedStock(null)}
      />
    </div>
  );
}
