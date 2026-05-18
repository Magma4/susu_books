"use client";

import { useEffect, useState } from "react";

interface PinAuthScreenProps {
  onUnlock: () => void;
  businessName?: string;
}

type AuthStep = "login" | "setup" | "confirm";

export default function PinAuthScreen({ onUnlock, businessName = "Ama's Market Stall" }: PinAuthScreenProps) {
  const [pin, setPin] = useState<string[]>([]);
  const [step, setStep] = useState<AuthStep>("setup");
  const [setupPin, setSetupPin] = useState<string[]>([]);
  const [error, setError] = useState<string>("");
  const [isUnlocked, setIsUnlocked] = useState(false);
  const [shake, setShake] = useState(false);

  // Load state from localStorage on mount
  useEffect(() => {
    const savedPin = localStorage.getItem("susu_books_pin");
    if (savedPin) {
      setStep("login");
    } else {
      setStep("setup");
    }
  }, []);

  // Trigger shake effect reset
  useEffect(() => {
    if (shake) {
      const t = setTimeout(() => setShake(false), 450);
      return () => clearTimeout(t);
    }
  }, [shake]);

  // Handle number click
  const handleNumber = (num: string) => {
    if (pin.length >= 4) return;
    setError("");
    
    // Haptic feedback for tap
    if (typeof navigator !== "undefined" && navigator.vibrate) {
      navigator.vibrate(15);
    }

    const nextPin = [...pin, num];
    setPin(nextPin);

    // Check if 4 digits are completed
    if (nextPin.length === 4) {
      // Small timeout to allow the final dot to light up visually
      setTimeout(() => {
        handleComplete(nextPin);
      }, 200);
    }
  };

  // Handle backspace
  const handleBackspace = () => {
    if (pin.length === 0) return;
    setError("");
    if (typeof navigator !== "undefined" && navigator.vibrate) {
      navigator.vibrate(10);
    }
    setPin(pin.slice(0, -1));
  };

  // Process completed PIN
  const handleComplete = (completedPin: string[]) => {
    const pinStr = completedPin.join("");

    if (step === "login") {
      const savedPin = localStorage.getItem("susu_books_pin");
      if (pinStr === savedPin) {
        // Unlock Success
        if (typeof navigator !== "undefined" && navigator.vibrate) {
          navigator.vibrate([30, 30]);
        }
        setIsUnlocked(true);
        setTimeout(() => {
          onUnlock();
        }, 300);
      } else {
        // Unlock Mismatch
        if (typeof navigator !== "undefined" && navigator.vibrate) {
          navigator.vibrate([100, 50, 100]);
        }
        setShake(true);
        setError("Incorrect PIN. Please try again.");
        setPin([]);
      }
    } else if (step === "setup") {
      setSetupPin(completedPin);
      setPin([]);
      setStep("confirm");
    } else if (step === "confirm") {
      const firstPinStr = setupPin.join("");
      if (pinStr === firstPinStr) {
        // Setup Success
        localStorage.setItem("susu_books_pin", pinStr);
        if (typeof navigator !== "undefined" && navigator.vibrate) {
          navigator.vibrate([30, 30]);
        }
        setIsUnlocked(true);
        setTimeout(() => {
          onUnlock();
        }, 300);
      } else {
        // Setup Mismatch
        if (typeof navigator !== "undefined" && navigator.vibrate) {
          navigator.vibrate([100, 50, 100]);
        }
        setShake(true);
        setError("PINs do not match. Start again.");
        setPin([]);
        setStep("setup");
      }
    }
  };

  // Reset PIN (Emergency recovery / reset logic)
  const handleReset = () => {
    if (confirm("Are you sure you want to reset your lock PIN? All local locks will be cleared.")) {
      localStorage.removeItem("susu_books_pin");
      setStep("setup");
      setPin([]);
      setError("");
    }
  };

  // Render UI labels based on current step
  const getHeaderLabel = () => {
    if (step === "login") return "Welcome Back";
    if (step === "setup") return "Create Secure PIN";
    return "Confirm PIN";
  };

  const getSubLabel = () => {
    if (step === "login") return `Enter your 4-digit security PIN to unlock your ledger.`;
    if (step === "setup") return "Set a 4-digit passcode to protect your business records from onlookers.";
    return "Type your 4-digit PIN again to confirm.";
  };

  return (
    <div
      className={`
        fixed inset-0 z-[9999] flex flex-col items-center justify-center p-4
        bg-slate-950 overflow-hidden transition-all duration-300
        ${isUnlocked ? "opacity-0 scale-105 pointer-events-none" : "opacity-100 scale-100"}
      `}
    >
      {/* Styles for shake animation & glowing orbs */}
      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes shake {
          0%, 100% { transform: translateX(0); }
          15%, 45%, 75% { transform: translateX(-8px); }
          30%, 60%, 90% { transform: translateX(8px); }
        }
        .animate-shake {
          animation: shake 0.45s cubic-bezier(.36,.07,.19,.97) both;
        }
      `}} />

      {/* Floating Ambient Glowing Background Orbs */}
      <div className="absolute top-1/4 left-1/4 h-80 w-80 rounded-full bg-primary-800/10 blur-[100px] pointer-events-none animate-pulse" />
      <div className="absolute bottom-1/4 right-1/4 h-96 w-96 rounded-full bg-accent-800/10 blur-[120px] pointer-events-none animate-pulse" style={{ animationDelay: "2s" }} />

      <div className="w-full max-w-sm flex flex-col items-center space-y-8 z-10">
        
        {/* Branding & Header */}
        <div className="text-center space-y-3">
          <div className="h-16 w-16 bg-gradient-to-tr from-primary-900 to-primary-700 rounded-3xl mx-auto flex items-center justify-center shadow-lg border border-primary-500/20">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
          </div>
          <div className="space-y-1">
            <h2 className="text-2xl font-bold tracking-tight text-white font-sans">
              {getHeaderLabel()}
            </h2>
            <p className="text-2xs text-primary-200 tracking-wider font-semibold uppercase">
              {businessName}
            </p>
          </div>
          <p className="text-xs text-slate-400 max-w-xs mx-auto leading-relaxed">
            {getSubLabel()}
          </p>
        </div>

        {/* PIN Indicator dots */}
        <div className={`flex items-center gap-6 py-2 ${shake ? "animate-shake" : ""}`}>
          {[0, 1, 2, 3].map((index) => {
            const isActive = pin.length > index;
            return (
              <div
                key={index}
                className={`
                  h-4.5 w-4.5 rounded-full border-2 transition-all duration-150
                  ${isActive 
                    ? "bg-gradient-to-tr from-accent-600 to-accent-400 border-accent-400 scale-110 shadow-[0_0_12px_rgba(245,127,23,0.5)]" 
                    : "border-slate-700 bg-slate-900/40"
                  }
                `}
              />
            );
          })}
        </div>

        {/* Error Feedback */}
        <div className="h-6 text-center">
          {error && (
            <p className="text-xs font-semibold text-rose-500 animate-pulse">
              {error}
            </p>
          )}
        </div>

        {/* Touch Keypad */}
        <div className="w-full grid grid-cols-3 gap-y-4 gap-x-6 px-4">
          {["1", "2", "3", "4", "5", "6", "7", "8", "9"].map((num) => (
            <button
              key={num}
              type="button"
              onClick={() => handleNumber(num)}
              className="
                h-16 w-16 rounded-full mx-auto flex items-center justify-center
                bg-slate-900/50 border border-slate-800/80 text-white font-sans font-semibold text-xl
                hover:bg-slate-800/80 hover:border-slate-700/80
                active:scale-90 transition-all duration-100 shadow-sm
              "
            >
              {num}
            </button>
          ))}
          
          {/* Bottom Row: Reset/Back, 0, Backspace */}
          <button
            type="button"
            onClick={handleReset}
            className="
              h-16 w-16 rounded-full mx-auto flex items-center justify-center
              text-slate-500 hover:text-slate-300 text-2xs font-semibold uppercase tracking-wider
              active:scale-95 transition-all
            "
          >
            {step === "login" ? "Reset" : "Cancel"}
          </button>
          
          <button
            type="button"
            onClick={() => handleNumber("0")}
            className="
              h-16 w-16 rounded-full mx-auto flex items-center justify-center
              bg-slate-900/50 border border-slate-800/80 text-white font-sans font-semibold text-xl
              hover:bg-slate-800/80 hover:border-slate-700/80
              active:scale-90 transition-all duration-100 shadow-sm
            "
          >
            0
          </button>
          
          <button
            type="button"
            onClick={handleBackspace}
            aria-label="Delete"
            className="
              h-16 w-16 rounded-full mx-auto flex items-center justify-center
              text-slate-400 hover:text-slate-200
              active:scale-90 transition-all duration-100
            "
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2M3 12l6.414 6.414A2 2 0 0010.828 19h7.172a2 2 0 002-2V7a2 2 0 00-2-2h-7.172a2 2 0 00-1.414.586L3 12z" />
            </svg>
          </button>
        </div>

      </div>
    </div>
  );
}
