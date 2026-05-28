import { Tag } from "antd";

interface Props {
  signal: "strong_buy" | "buy" | "watch";
}

const signalConfig = {
  strong_buy: { color: "red", text: "强烈推荐" },
  buy: { color: "orange", text: "建议关注" },
  watch: { color: "default", text: "观望" },
};

export default function StatusBadge({ signal }: Props) {
  const cfg = signalConfig[signal];
  return <Tag color={cfg.color}>{cfg.text}</Tag>;
}
