import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, tzOffset } from "../api";
import { translateApiError } from "../i18n/apiErrors";

/** base64url → Uint8Array (the format PushManager.subscribe expects). */
function urlBase64ToUint8Array(base64String) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = window.atob(base64);
  const output = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i += 1) output[i] = raw.charCodeAt(i);
  return output;
}

/**
 * Bell toggle in the dashboard header: opt-in web-push reminders.
 * The permission prompt only ever appears on a user click, never on load.
 */
export default function RemindersToggle() {
  const { t, i18n } = useTranslation();
  // loading → on | off | denied | unsupported | dev (no service worker)
  const [state, setState] = useState("loading");
  const [error, setError] = useState("");

  const supported =
    typeof window !== "undefined" &&
    "Notification" in window &&
    "serviceWorker" in navigator &&
    "PushManager" in window;

  useEffect(() => {
    if (!supported) {
      setState("unsupported");
      return;
    }
    if (window.Notification.permission === "denied") {
      setState("denied");
      return;
    }
    api
      .remindersStatus()
      .then(({ subscribed }) => {
        const granted = window.Notification.permission === "granted";
        setState(subscribed && granted ? "on" : "off");
      })
      .catch(() => setState("off"));
  }, []);

  const disable = async () => {
    try {
      const registration = await navigator.serviceWorker.getRegistration();
      const existing = registration
        ? await registration.pushManager.getSubscription()
        : null;
      if (existing) {
        await api.remindersUnsubscribe(existing.endpoint);
        await existing.unsubscribe();
      }
      setState("off");
    } catch (err) {
      setError(translateApiError(t, err.message));
    }
  };

  const enable = async () => {
    const permission = await window.Notification.requestPermission();
    if (permission !== "granted") {
      setState(permission === "denied" ? "denied" : "off");
      return;
    }
    // The SW only registers in production (pwa.js) — without it there is
    // nowhere to receive the push.
    const registration = await navigator.serviceWorker.getRegistration();
    if (!registration) {
      setState("dev");
      return;
    }
    let subscription = await registration.pushManager.getSubscription();
    if (!subscription) {
      const { publicKey } = await api.remindersPublicKey();
      subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(publicKey),
      });
    }
    const { keys } = subscription.toJSON();
    await api.remindersSubscribe({
      endpoint: subscription.endpoint,
      keys: { p256dh: keys.p256dh, auth: keys.auth },
      tz_offset: tzOffset(),
      lang: i18n.language.startsWith("fr") ? "fr" : "en",
    });
    setState("on");
  };

  const toggle = () => {
    setError("");
    const action = state === "on" ? disable : enable;
    action().catch((err) => setError(translateApiError(t, err.message)));
  };

  if (state === "loading") return null;

  const labels = {
    on: t("reminders.disable"),
    off: t("reminders.enable"),
    denied: t("reminders.denied"),
    unsupported: t("reminders.unsupported"),
    dev: t("reminders.devOnly"),
  };
  const label = labels[state] ?? t("reminders.enable");
  const isOn = state === "on";
  const blocked = state === "denied" || state === "unsupported" || state === "dev";

  return (
    <div className="reminders">
      <button
        type="button"
        className={`bell ${isOn ? "is-on" : ""}`}
        onClick={toggle}
        disabled={blocked}
        aria-pressed={isOn}
        aria-label={label}
        title={label}
      >
        <svg
          viewBox="0 0 24 24"
          width="18"
          height="18"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.7 21a2 2 0 0 1-3.4 0" />
        </svg>
      </button>
      {error && <p className="error reminders-error">{error}</p>}
    </div>
  );
}
