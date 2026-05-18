"use client";

import { useEffect, useState, useRef } from "react";

export interface TraderProfile {
  id: string;
  name: string;
  pinHash: string;
}

interface PinAuthScreenProps {
  onUnlock: (profile: TraderProfile) => void;
  businessName?: string;
}

type AuthStep = "select_profile" | "login" | "create_profile_name" | "setup_pin" | "confirm_pin";

export default function PinAuthScreen({ onUnlock, businessName = "Ama's Market Stall" }: PinAuthScreenProps) {
  const [profiles, setProfiles] = useState<TraderProfile[]>([]);
  const [step, setStep] = useState<AuthStep>("select_profile");
  const [activeProfile, setActiveProfile] = useState<TraderProfile | null>(null);
  
  const [newProfileName, setNewProfileName] = useState("");
  const [pin, setPin] = useState<string[]>([]);
  const [setupPin, setSetupPin] = useState<string[]>([]);
  
  const [error, setError] = useState<string>("");
  const [isUnlocked, setIsUnlocked] = useState(false);
  const [shake, setShake] = useState(false);

  const inputRef = useRef<HTMLInputElement>(null);

  // Load profiles from localStorage on mount
  useEffect(() => {
    try {
      const saved = localStorage.getItem("susu_books_profiles");
      if (saved) {
        const parsed = JSON.parse(saved) as TraderProfile[];
        if (parsed.length > 0) {
          setProfiles(parsed);
          setStep("select_profile");
          return;
        }
      }
    } catch (e) {}
    
    // Fallback/Legacy migration: check for old susu_books_pin
    const legacyPin = localStorage.getItem("susu_books_pin");
    if (legacyPin) {
      const legacyProfile: TraderProfile = { id: "legacy", name: "Owner", pinHash: legacyPin };
      const migrated = [legacyProfile];
      localStorage.setItem("susu_books_profiles", JSON.stringify(migrated));
      localStorage.removeItem("susu_books_pin");
      setProfiles(migrated);
      setStep("select_profile");
      return;
    }

    setStep("create_profile_name");
  }, []);

  // Trigger shake effect reset
  useEffect(() => {
    if (shake) {
      const t = setTimeout(() => setShake(false), 450);
      return () => clearTimeout(t);
    }
  }, [shake]);

  // Focus input when creating profile
  useEffect(() => {
    if (step === "create_profile_name" && inputRef.current) {
      inputRef.current.focus();
    }
  }, [step]);

  // Handle number click
  const handleNumber = (num: string) => {
    if (pin.length >= 4) return;
    setError("");
    
    if (typeof navigator !== "undefined" && navigator.vibrate) {
      navigator.vibrate(15);
    }

    const nextPin = [...pin, num];
    setPin(nextPin);

    if (nextPin.length === 4) {
      setTimeout(() => {
        handleComplete(nextPin);
      }, 200);
    }
  };

  const handleBackspace = () => {
    if (pin.length === 0) return;
    setError("");
    if (typeof navigator !== "undefined" && navigator.vibrate) {
      navigator.vibrate(10);
    }
    setPin(pin.slice(0, -1));
  };

  const handleComplete = (completedPin: string[]) => {
    const pinStr = completedPin.join("");

    if (step === "login" && activeProfile) {
      if (pinStr === activeProfile.pinHash) {
        // Unlock Success
        if (typeof navigator !== "undefined" && navigator.vibrate) {
          navigator.vibrate([30, 30]);
        }
        setIsUnlocked(true);
        setTimeout(() => {
          onUnlock(activeProfile);
        }, 300);
      } else {
        // Unlock Mismatch
        if (typeof navigator !== "undefined" && navigator.vibrate) {
          navigator.vibrate([100, 50, 100]);
        }
        setShake(true);
        setError("Incorrect PIN.");
        setPin([]);
      }
    } else if (step === "setup_pin") {
      setSetupPin(completedPin);
      setPin([]);
      setStep("confirm_pin");
    } else if (step === "confirm_pin") {
      const firstPinStr = setupPin.join("");
      if (pinStr === firstPinStr) {
        // Setup Success
        const newProfile: TraderProfile = {
          id: Date.now().toString(36),
          name: newProfileName.trim() || "Trader",
          pinHash: pinStr,
        };
        const updatedProfiles = [...profiles, newProfile];
        localStorage.setItem("susu_books_profiles", JSON.stringify(updatedProfiles));
        setProfiles(updatedProfiles);
        
        if (typeof navigator !== "undefined" && navigator.vibrate) {
          navigator.vibrate([30, 30]);
        }
        setIsUnlocked(true);
        setTimeout(() => {
          onUnlock(newProfile);
        }, 300);
      } else {
        // Setup Mismatch
        if (typeof navigator !== "undefined" && navigator.vibrate) {
          navigator.vibrate([100, 50, 100]);
        }
        setShake(true);
        setError("PINs do not match.");
        setPin([]);
        setStep("setup_pin");
      }
    }
  };

  const handleReset = () => {
    if (confirm("Are you sure you want to completely reset the lock screen and clear ALL profiles?")) {
      localStorage.removeItem("susu_books_profiles");
      setProfiles([]);
      setStep("create_profile_name");
      setNewProfileName("");
      setPin([]);
      setError("");
    }
  };

  const handleBackToProfiles = () => {
    setStep("select_profile");
    setActiveProfile(null);
    setPin([]);
    setError("");
  };

  const startCreateProfile = () => {
    setNewProfileName("");
    setPin([]);
    setSetupPin([]);
    setError("");
    setStep("create_profile_name");
  };

  const selectProfile = (profile: TraderProfile) => {
    setActiveProfile(profile);
    setPin([]);
    setError("");
    setStep("login");
  };

  const handleNameSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (newProfileName.trim().length === 0) {
      setError("Please enter a name");
      return;
    }
    setError("");
    setStep("setup_pin");
  };

  const getHeaderLabel = () => {
    if (step === "select_profile") return "Who is using the ledger?";
    if (step === "login") return `Welcome, ${activeProfile?.name}`;
    if (step === "create_profile_name") return "Create Profile";
    if (step === "setup_pin") return "Create PIN";
    return "Confirm PIN";
  };

  const getSubLabel = () => {
    if (step === "select_profile") return "Select your profile to unlock.";
    if (step === "login") return "Enter your personal 4-digit security PIN.";
    if (step === "create_profile_name") return "What is your name?";
    if (step === "setup_pin") return `Set a 4-digit passcode for ${newProfileName}.`;
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

      <div className="absolute top-1/4 left-1/4 h-80 w-80 rounded-full bg-primary-800/10 blur-[100px] pointer-events-none animate-pulse" />
      <div className="absolute bottom-1/4 right-1/4 h-96 w-96 rounded-full bg-accent-800/10 blur-[120px] pointer-events-none animate-pulse" style={{ animationDelay: "2s" }} />

      <div className="w-full max-w-sm flex flex-col items-center space-y-8 z-10">
        
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

        {/* Dynamic Content based on Step */}
        {step === "select_profile" ? (
          <div className="w-full space-y-4 px-4">
            <div className="grid grid-cols-2 gap-4">
              {profiles.map(p => (
                <button
                  key={p.id}
                  onClick={() => selectProfile(p)}
                  className="flex flex-col items-center justify-center p-4 rounded-2xl bg-slate-900/60 border border-slate-800 hover:bg-slate-800 hover:border-slate-700 transition-all shadow-sm active:scale-95"
                >
                  <div className="h-12 w-12 rounded-full bg-primary-900 text-primary-200 flex items-center justify-center text-lg font-bold mb-3 border border-primary-700/50">
                    {p.name.charAt(0).toUpperCase()}
                  </div>
                  <span className="text-sm font-medium text-slate-200 truncate w-full text-center">
                    {p.name}
                  </span>
                </button>
              ))}
            </div>
            
            <button
              onClick={startCreateProfile}
              className="w-full flex items-center justify-center gap-2 p-4 rounded-2xl bg-transparent border-2 border-dashed border-slate-800 text-slate-400 hover:text-slate-300 hover:border-slate-700 hover:bg-slate-900/40 transition-all active:scale-95"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" />
              </svg>
              <span className="font-medium text-sm">Add New Profile</span>
            </button>

            <button
              type="button"
              onClick={handleReset}
              className="mt-8 mx-auto block text-slate-600 hover:text-slate-400 text-2xs font-semibold uppercase tracking-wider transition-all"
            >
              Reset All
            </button>
          </div>
        ) : step === "create_profile_name" ? (
          <form onSubmit={handleNameSubmit} className="w-full px-8 space-y-6">
            <input
              ref={inputRef}
              type="text"
              value={newProfileName}
              onChange={(e) => {
                setNewProfileName(e.target.value);
                setError("");
              }}
              placeholder="e.g. Ama or Kofi"
              className="w-full bg-slate-900/60 border border-slate-700 text-white rounded-xl px-4 py-4 text-center text-lg focus:outline-none focus:ring-2 focus:ring-primary-500 placeholder:text-slate-600"
              maxLength={20}
            />
            {error && (
              <p className="text-xs font-semibold text-rose-500 text-center animate-pulse">
                {error}
              </p>
            )}
            <div className="flex gap-4">
              {profiles.length > 0 && (
                <button
                  type="button"
                  onClick={handleBackToProfiles}
                  className="flex-1 py-4 rounded-xl bg-slate-800 text-slate-300 font-semibold hover:bg-slate-700 transition-colors"
                >
                  Cancel
                </button>
              )}
              <button
                type="submit"
                className="flex-1 py-4 rounded-xl bg-primary-600 text-white font-semibold shadow-lg hover:bg-primary-500 transition-colors"
              >
                Next
              </button>
            </div>
          </form>
        ) : (
          <>
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
              
              <button
                type="button"
                onClick={step === "login" ? handleBackToProfiles : startCreateProfile}
                className="
                  h-16 w-16 rounded-full mx-auto flex items-center justify-center
                  text-slate-500 hover:text-slate-300 text-2xs font-semibold uppercase tracking-wider
                  active:scale-95 transition-all
                "
              >
                {step === "login" ? "Back" : "Cancel"}
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
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2M3 12l6.414 6.414A2 2 0 0010.828 19h7.172a2 2 0 002-2V7a2 2 0 00-1.414.586L3 12z" />
                </svg>
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
