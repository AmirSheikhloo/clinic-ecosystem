import { Icon } from "@/components/ui/Icon";

type Props = {
  channel?: string | null;
  className?: string;
};

/** Compact ONLINE_WEB / ONLINE_BOT chip beside patient names. Manual staff → no icon. */
export function BookingChannelIndicator({ channel, className = "" }: Props) {
  if (channel === "ONLINE_WEB") {
    return (
      <span
        className={`ds-channel-chip ${className}`.trim()}
        title="رزرو از طریق سایت"
        aria-label="رزرو از طریق سایت"
        data-testid="channel-web"
        data-channel="ONLINE_WEB"
      >
        <Icon name="globe" size="sm" />
      </span>
    );
  }
  if (channel === "ONLINE_BOT") {
    return (
      <span
        className={`ds-channel-chip ${className}`.trim()}
        title="رزرو از طریق ربات"
        aria-label="رزرو از طریق ربات"
        data-testid="channel-bot"
        data-channel="ONLINE_BOT"
      >
        <Icon name="bot" size="sm" />
      </span>
    );
  }
  return null;
}
