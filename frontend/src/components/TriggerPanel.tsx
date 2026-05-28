import { Button, Progress, Space, Tag, Typography, message, Alert } from "antd";
import {
  ThunderboltOutlined,
  ClockCircleOutlined,
  StopOutlined,
} from "@ant-design/icons";
import { useState, useCallback, useRef } from "react";
import type { RunStatus } from "../types/stock";
import {
  triggerScreening,
  cancelScreening,
  fetchTaskStatus,
} from "../services/api";

const { Text } = Typography;

interface Props {
  lastRun: RunStatus | null;
  isTradingDay: boolean;
  onRefresh: () => void;
}

export default function TriggerPanel({ lastRun, isTradingDay, onRefresh }: Props) {
  const [loading, setLoading] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [progress, setProgress] = useState({ stage: "", msg: "", percent: 0 });
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const startPolling = useCallback(
    (tid: string) => {
      if (pollingRef.current) clearInterval(pollingRef.current);
      pollingRef.current = setInterval(async () => {
        try {
          const data = await fetchTaskStatus(tid);
          setProgress(data.progress);
          if (data.run_info?.status === "completed" || data.run_info?.status === "failed") {
            if (pollingRef.current) clearInterval(pollingRef.current);
            pollingRef.current = null;
            setLoading(false);
            setTaskId(null);
            if (data.run_info?.status === "completed") {
              message.success(`筛选完成！推荐 ${data.run_info.passed_all} 只股票`);
            } else {
              message.error(`筛选失败: ${data.run_info?.error || "未知错误"}`);
            }
            onRefresh();
          }
        } catch {
          // polling silently fails
        }
      }, 1000);
    },
    [onRefresh]
  );

  const handleTrigger = async () => {
    setLoading(true);
    setProgress({ stage: "", msg: "正在启动...", percent: 0 });
    try {
      const data = await triggerScreening();
      if (data.warning) {
        message.warning(data.warning);
      }
      if (data.task_id) {
        setTaskId(data.task_id);
        startPolling(data.task_id);
      }
    } catch (e: any) {
      message.error("触发筛选失败: " + (e.message || "未知错误"));
      setLoading(false);
    }
  };

  const handleCancel = async () => {
    try {
      await cancelScreening();
      if (pollingRef.current) clearInterval(pollingRef.current);
      pollingRef.current = null;
      setLoading(false);
      setTaskId(null);
      setProgress({ stage: "", msg: "已取消", percent: 0 });
      message.info("已取消筛选");
    } catch {
      // ignore
    }
  };

  const isRunning = loading && taskId !== null;

  return (
    <div style={{ marginBottom: 24 }}>
      <Space wrap>
        <Button
          type="primary"
          size="large"
          icon={<ThunderboltOutlined />}
          loading={loading && !isRunning}
          onClick={handleTrigger}
          disabled={isRunning}
        >
          手动触发筛选
        </Button>
        {isRunning && (
          <Button danger size="large" icon={<StopOutlined />} onClick={handleCancel}>
            取消
          </Button>
        )}
        {lastRun?.finished_at && !isRunning && (
          <Text type="secondary">
            <ClockCircleOutlined /> 上次运行: {new Date(lastRun.finished_at).toLocaleString("zh-CN")}
          </Text>
        )}
        {!isTradingDay && (
          <Tag color="default">非交易日，手动触发结果可能不完整</Tag>
        )}
      </Space>

      {isRunning && (
        <div style={{ marginTop: 16 }}>
          <Progress percent={progress.percent} status="active" strokeColor="#cf1322" />
          <Text type="secondary">{progress.msg}</Text>
        </div>
      )}
    </div>
  );
}
