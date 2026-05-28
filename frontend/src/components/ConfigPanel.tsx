import { useEffect, useState, useCallback } from "react";
import {
  Card, Form, InputNumber, Switch, Input, Button, Collapse,
  Typography, message, Spin, Alert, Popconfirm, Space,
} from "antd";
import { SettingOutlined, UndoOutlined, SaveOutlined, ReloadOutlined } from "@ant-design/icons";
import type { ConfigItem, ConfigResponse } from "../types/stock";
import { fetchConfig, updateConfig, resetConfig } from "../services/api";

const { Title } = Typography;

export default function ConfigPanel() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<Record<string, boolean>>({});
  const [data, setData] = useState<ConfigResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [changedKeys, setChangedKeys] = useState<Set<string>>(new Set());
  const [formValues, setFormValues] = useState<Record<string, unknown>>({});

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchConfig();
      setData(res);
      // 构建初始值
      const vals: Record<string, unknown> = {};
      for (const item of res.config) {
        vals[item.key] = item.value;
      }
      setFormValues(vals);
      setChangedKeys(new Set());
    } catch {
      setError("无法加载配置，请确认后端服务正常");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleValueChange = (key: string, value: unknown) => {
    setFormValues((prev) => ({ ...prev, [key]: value }));
    setChangedKeys((prev) => {
      const next = new Set(prev);
      // 对比原始值判断是否有变化
      const original = data?.config.find((c) => c.key === key)?.value;
      if (value === original || String(value) === String(original)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  const handleSaveOne = async (key: string) => {
    const val = formValues[key];
    setSaving((prev) => ({ ...prev, [key]: true }));
    try {
      await updateConfig(key, val as string | number | boolean);
      message.success(`已保存: ${key}`);
      setChangedKeys((prev) => {
        const next = new Set(prev);
        next.delete(key);
        return next;
      });
      // 更新 data 中的值
      if (data) {
        setData({
          ...data,
          config: data.config.map((c) => (c.key === key ? { ...c, value: val as never } : c)),
        });
      }
    } catch {
      message.error(`保存失败: ${key}`);
    } finally {
      setSaving((prev) => ({ ...prev, [key]: false }));
    }
  };

  const handleSaveGroup = async (items: ConfigItem[]) => {
    const changedGroupKeys = items.filter((c) => changedKeys.has(c.key));
    if (!changedGroupKeys.length) {
      message.info("该分组无修改");
      return;
    }
    const batch: Record<string, string | number | boolean> = {};
    for (const c of changedGroupKeys) {
      batch[c.key] = formValues[c.key] as string | number | boolean;
    }
    try {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const { updateConfigBatch } = await import("../services/api") as any;
      await (updateConfigBatch as typeof import("../services/api").updateConfigBatch)(batch);
      message.success(`已保存 ${Object.keys(batch).length} 项`);
      setChangedKeys(new Set());
      await load();
    } catch {
      message.error("批量保存失败");
    }
  };

  const handleReset = async () => {
    try {
      await resetConfig();
      message.success("已重置为默认值");
      await load();
    } catch {
      message.error("重置失败");
    }
  };

  const renderInput = (item: ConfigItem) => {
    const val = formValues[item.key];
    switch (item.type) {
      case "float":
      case "int":
        return (
          <InputNumber
            value={val as number}
            onChange={(v) => handleValueChange(item.key, v ?? item.value)}
            min={item.min}
            max={item.max}
            step={item.step ?? 0.1}
            size="small"
            style={{ width: 140 }}
          />
        );
      case "bool":
        return (
          <Switch
            checked={val as boolean}
            onChange={(v) => handleValueChange(item.key, v)}
            size="small"
          />
        );
      case "text":
        return (
          <Input
            value={val as string}
            onChange={(e) => handleValueChange(item.key, e.target.value)}
            size="small"
            style={{ width: 120 }}
          />
        );
    }
  };

  if (loading) return <Spin size="large" style={{ display: "block", margin: "60px auto" }} />;
  if (error) return <Alert type="error" message={error} showIcon action={<a onClick={load}>重试</a>} />;
  if (!data) return null;

  // 按 group 分组
  const groupMap: Record<string, ConfigItem[]> = {};
  for (const item of data.config) {
    const g = data.groups ? Object.keys(data.groups).find((k) =>
      data.groups[k].some((gi) => gi.key === item.key)
    ) || "其他" : "其他";
    groupMap[g] = groupMap[g] || [];
    groupMap[g].push(item);
  }

  const groupOrder = Object.keys(groupMap);

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Title level={5} style={{ margin: 0 }}>
          <SettingOutlined /> 策略参数配置
          {changedKeys.size > 0 && (
            <span style={{ fontSize: 13, color: "#faad14", marginLeft: 12, fontWeight: 400 }}>
              {changedKeys.size} 项未保存
            </span>
          )}
        </Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={load} size="small">刷新</Button>
          <Popconfirm
            title="确定要重置所有配置为默认值吗？"
            onConfirm={handleReset}
            okText="确定"
            cancelText="取消"
          >
            <Button icon={<UndoOutlined />} danger size="small">重置默认值</Button>
          </Popconfirm>
        </Space>
      </div>

      <Collapse
        size="small"
        defaultActiveKey={groupOrder.slice(0, 2)}
        items={groupOrder.map((group) => {
          const items = groupMap[group];
          return {
            key: group,
            label: <span><SettingOutlined /> {group}（{items.length} 项）</span>,
            extra: groupOrder.length > 1 ? (
              <Button
                size="small"
                type="link"
                icon={<SaveOutlined />}
                onClick={(e) => {
                  e.stopPropagation();
                  handleSaveGroup(items);
                }}
              >
                保存本组
              </Button>
            ) : undefined,
            children: (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))", gap: 8 }}>
                {items.map((item) => (
                  <Card
                    key={item.key}
                    size="small"
                    styles={{ body: { padding: "8px 12px" } }}
                  >
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 13, fontWeight: 500 }}>{item.desc}</div>
                        <div style={{ fontSize: 11, color: "#999", marginTop: 2 }}>
                          {item.key}
                          {item.min !== undefined && item.max !== undefined && (
                            <span> · 范围 [{item.min}, {item.max}]</span>
                          )}
                        </div>
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
                        {renderInput(item)}
                        <Button
                          type={changedKeys.has(item.key) ? "primary" : "default"}
                          size="small"
                          icon={<SaveOutlined />}
                          loading={saving[item.key]}
                          onClick={() => handleSaveOne(item.key)}
                          disabled={!changedKeys.has(item.key)}
                        />
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            ),
          };
        })}
      />

      {groupOrder.length === 0 && <Alert type="info" message="暂无配置项" />}
    </div>
  );
}
