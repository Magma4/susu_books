"use client";
/**
 * OllamaOfflineScreen — Warm, friendly setup guide shown when the AI backend
 * is unreachable. Non-technical language, step-by-step instructions.
 */

import { useState } from "react";

interface OllamaOfflineScreenProps {
  onRetry: () => void;
  isRetrying?: boolean;
  /** True if the FastAPI server itself is unreachable (vs Ollama being down) */
  isBackendDown?: boolean;
}

export default function OllamaOfflineScreen({
  onRetry,
  isRetrying = false,
  isBackendDown = false,
}: OllamaOfflineScreenProps) {
  const [copied, setCopied] = useState<string | null>(null);

  const copyCmd = (cmd: string, key: string) => {
    navigator.clipboard.writeText(cmd).then(() => {
      setCopied(key);
      setTimeout(() => setCopied(null), 2000);
    });
  };

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center px-4 py-8">
      {/* Logo */}
      <div className="h-16 w-16 bg-primary-900 rounded-2xl flex items-center justify-center mb-4 shadow-voice">
        <BookIcon />
      </div>

      <h1 className="text-2xl font-bold text-text-primary mb-1">Susu Books</h1>
      <p className="text-sm text-text-secondary mb-8">
        Your offline business copilot
      </p>

      {/* Main card */}
      <div className="w-full max-w-md bg-white rounded-2xl border border-border shadow-card p-6">
        <div className="text-center mb-6">
          <div className="text-5xl mb-3">{isBackendDown ? "🔌" : "🤖"}</div>
          <h2 className="text-lg font-bold text-text-primary">
            {isBackendDown
              ? "Start the Susu Books server"
              : "Connect Susu Books to its AI brain"}
          </h2>
          <p className="text-sm text-text-secondary mt-2 leading-relaxed">
            {isBackendDown
              ? "The Susu Books backend isn't running yet. Follow the steps below to start it."
              : "Susu Books uses Ollama to run the Gemma 4 AI on your computer — no internet needed. It takes 2 minutes to set up."}
          </p>
        </div>

        {/* Setup steps */}
        <div className="space-y-3">
          {isBackendDown ? (
            <BackendSetupSteps copyCmd={copyCmd} copied={copied} />
          ) : (
            <OllamaSetupSteps copyCmd={copyCmd} copied={copied} />
          )}
        </div>
      </div>

      {/* Retry button */}
      <button
        onClick={onRetry}
        disabled={isRetrying}
        className="
          mt-6 btn-primary px-8 py-3 text-base flex items-center gap-2
          disabled:opacity-60
        "
      >
        {isRetrying ? (
          <>
            <span className="h-4 w-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
            Checking…
          </>
        ) : (
          <>
            <span>↻</span>
            Check Again
          </>
        )}
      </button>

      <p className="mt-4 text-xs text-text-disabled text-center max-w-xs">
        Once Ollama is running and the model is loaded, click &ldquo;Check Again&rdquo; — Susu Books will connect automatically.
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Steps sub-components
// ---------------------------------------------------------------------------

function OllamaSetupSteps({
  copyCmd,
  copied,
}: {
  copyCmd: (cmd: string, key: string) => void;
  copied: string | null;
}) {
  const steps = [
    {
      key: "install",
      number: "1",
      title: "Install Ollama",
      description: "Download and install Ollama on your computer",
      action: {
        label: "ollama.ai/download",
        href: "https://ollama.ai/download",
        isLink: true,
      },
    },
    {
      key: "pull",
      number: "2",
      title: "Download the Gemma 4 model",
      description: "Open your terminal and run:",
      code: "ollama pull gemma4:31b-instruct",
      note: "You can also use gemma4:26b-a4b-instruct if that fits your machine better.",
    },
    {
      key: "serve",
      number: "3",
      title: "Start Ollama",
      description: "Ollama should start automatically after install. Or run:",
      code: "ollama serve",
    },
  ];

  return (
    <>
      {steps.map((step) => (
        <SetupStep
          key={step.key}
          step={step}
          copied={copied}
          onCopy={copyCmd}
        />
      ))}
    </>
  );
}

function BackendSetupSteps({
  copyCmd,
  copied,
}: {
  copyCmd: (cmd: string, key: string) => void;
  copied: string | null;
}) {
  const steps = [
    {
      key: "venv",
      number: "1",
      title: "Navigate to the backend folder",
      code: "cd backend && pip install -r requirements.txt",
    },
    {
      key: "start",
      number: "2",
      title: "Start the FastAPI server",
      code: "uvicorn main:app --host 0.0.0.0 --port 8000",
    },
    {
      key: "seed",
      number: "3",
      title: "(Optional) Load demo data",
      description: "Pre-populate with 2 weeks of sample transactions:",
      code: "python seed.py",
    },
  ];

  return (
    <>
      {steps.map((step) => (
        <SetupStep
          key={step.key}
          step={step}
          copied={copied}
          onCopy={copyCmd}
        />
      ))}
    </>
  );
}

interface Step {
  key: string;
  number: string;
  title: string;
  description?: string;
  code?: string;
  note?: string;
  action?: { label: string; href: string; isLink: boolean };
}

function SetupStep({
  step,
  copied,
  onCopy,
}: {
  step: Step;
  copied: string | null;
  onCopy: (cmd: string, key: string) => void;
}) {
  return (
    <div className="flex gap-3">
      {/* Number badge */}
      <div className="h-7 w-7 rounded-full bg-primary-surface text-primary-900 flex items-center justify-center flex-shrink-0 text-sm font-bold mt-0.5">
        {step.number}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-text-primary">{step.title}</p>
        {step.description && (
          <p className="text-xs text-text-secondary mt-0.5">{step.description}</p>
        )}
        {step.action && (
          <a
            href={step.action.href}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-primary-800 font-medium hover:underline mt-1 block"
          >
            → {step.action.label}
          </a>
        )}
        {step.code && (
          <div
            className="mt-1.5 flex items-center gap-2 bg-gray-900 rounded-lg px-3 py-2 cursor-pointer group"
            onClick={() => onCopy(step.code!, step.key)}
          >
            <code className="text-green-400 text-xs font-mono flex-1 truncate">
              {step.code}
            </code>
            <span className="text-gray-500 group-hover:text-gray-300 text-xs flex-shrink-0 transition-colors">
              {copied === step.key ? "✓ copied" : "copy"}
            </span>
          </div>
        )}
        {step.note && (
          <p className="text-2xs text-text-disabled mt-1">{step.note}</p>
        )}
      </div>
    </div>
  );
}

function BookIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      className="h-9 w-9 text-white"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
    </svg>
  );
}
