import { useState } from "react";
import { api, ApiError } from "../api";
import type { NewHostInput } from "../types";

interface Props {
  onCreated: () => void;
}

export default function AddHostForm({ onCreated }: Props) {
  const [name, setName] = useState("");
  const [address, setAddress] = useState("");
  const [description, setDescription] = useState("");
  const [expectedPorts, setExpectedPorts] = useState("");
  const [expectedHttpUrl, setExpectedHttpUrl] = useState("");
  const [authorized, setAuthorized] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (!authorized) {
      setError("You must confirm you own or are authorized to test this host before it can be added.");
      return;
    }

    const payload: NewHostInput = {
      name,
      address,
      description: description || undefined,
      expected_ports: expectedPorts
        ? expectedPorts
            .split(",")
            .map((p) => parseInt(p.trim(), 10))
            .filter((p) => !Number.isNaN(p))
        : undefined,
      expected_http_url: expectedHttpUrl || undefined,
      authorized_confirmation: authorized,
    };

    setSubmitting(true);
    try {
      await api.createHost(payload);
      setName("");
      setAddress("");
      setDescription("");
      setExpectedPorts("");
      setExpectedHttpUrl("");
      setAuthorized(false);
      onCreated();
    } catch (err) {
      if (err instanceof ApiError) {
        const detail = err.detail as any;
        const message = Array.isArray(detail?.detail)
          ? detail.detail.map((d: any) => d.msg).join("; ")
          : detail?.detail || err.message;
        setError(message);
      } else {
        setError("Something went wrong adding this host.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="panel" onSubmit={handleSubmit}>
      <h3>Add a host</h3>

      <div className="warning-banner">
        <strong>Authorized use only.</strong> Only add hosts you own or have
        explicit written authorization to test. Scanning or probing systems
        without authorization may be illegal in your jurisdiction.
      </div>

      <label>
        Name
        <input value={name} onChange={(e) => setName(e.target.value)} required />
      </label>
      <label>
        Address (single IP or hostname — no ranges)
        <input value={address} onChange={(e) => setAddress(e.target.value)} placeholder="192.168.1.10" required />
      </label>
      <label>
        Description (optional)
        <input value={description} onChange={(e) => setDescription(e.target.value)} />
      </label>
      <label>
        Expected open ports (optional, comma-separated — e.g. 22,80,443)
        <input value={expectedPorts} onChange={(e) => setExpectedPorts(e.target.value)} placeholder="22,80,443" />
      </label>
      <label>
        Expected HTTP health-check URL (optional)
        <input
          value={expectedHttpUrl}
          onChange={(e) => setExpectedHttpUrl(e.target.value)}
          placeholder="http://192.168.1.10/health"
        />
      </label>

      <label className="checkbox-label">
        <input type="checkbox" checked={authorized} onChange={(e) => setAuthorized(e.target.checked)} />
        I own this host, or I have explicit written authorization to test it.
      </label>

      {error && <div className="error-banner">{error}</div>}

      <button type="submit" disabled={submitting}>
        {submitting ? "Adding..." : "Add host"}
      </button>
    </form>
  );
}
