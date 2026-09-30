import { useState } from "react";
import { api } from "../api";
import { useNavigate } from "react-router-dom";

export default function NewHabit() {
  const [step, setStep] = useState(0);
  const [name, setName] = useState("");
  const [anchor, setAnchor] = useState("");
  const [tinyBehavior, setTinyBehavior] = useState("");
  const [celebration, setCelebration] = useState("");
  const [cueTime, setCueTime] = useState("");
  const navigate = useNavigate();

  const steps = [
    {
      title: "Choose your anchor",
      desc: "An existing routine you already do every day. This is your trigger.",
      placeholder: "e.g., pour my morning coffee",
      value: anchor,
      set: setAnchor,
    },
    {
      title: "Define a tiny behavior",
      desc: "Something so small it takes less than 30 seconds. Start absurdly small.",
      placeholder: "e.g., do 2 push-ups",
      value: tinyBehavior,
      set: setTinyBehavior,
    },
    {
      title: "Pick a celebration",
      desc: "Immediate positive emotion wires the habit into your brain. Make it fun!",
      placeholder: "e.g., say 'I'm strong!' and smile",
      value: celebration,
      set: setCelebration,
    },
  ];

  const submit = async () => {
    await api.createHabit({
      name,
      anchor,
      tiny_behavior: tinyBehavior,
      celebration,
      cue_time: cueTime,
    });
    navigate("/");
  };

  return (
    <div className="wizard">
      <h2>Design a Tiny Habit</h2>
      <p className="science">
        Based on BJ Fogg&apos;s Tiny Habits method — small behaviors + anchors +
        celebration = lasting change.
      </p>
      <div className="steps-indicator">
        {steps.map((_, i) => (
          <span key={i} className={i === step ? "active" : ""}>
            ●
          </span>
        ))}
      </div>
      <h3>{steps[step].title}</h3>
      <p>{steps[step].desc}</p>
      {step === 0 && (
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Short name (e.g., Drink water)"
          aria-label="Habit name"
        />
      )}
      <input
        value={steps[step].value}
        onChange={(e) => steps[step].set(e.target.value)}
        placeholder={steps[step].placeholder}
      />
      {step === 2 && (
        <input
          value={cueTime}
          onChange={(e) => setCueTime(e.target.value)}
          placeholder="Preferred time (optional, e.g., 08:00)"
        />
      )}
      <div className="wizard-nav">
        {step > 0 && (
          <button onClick={() => setStep(step - 1)}>Back</button>
        )}
        {step < 2 && (
          <button
            className="btn-primary"
            onClick={() => setStep(step + 1)}
            disabled={
              step === 0
                ? !name.trim() || !steps[0].value.trim()
                : !steps[step].value.trim()
            }
          >
            Next
          </button>
        )}
        {step === 2 && (
          <button
            className="btn-primary"
            onClick={submit}
            disabled={!celebration}
          >
            Create Habit
          </button>
        )}
      </div>
    </div>
  );
}
