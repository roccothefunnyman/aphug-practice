/* Voice singleton: read-aloud (SpeechSynthesis) and push-to-talk (SpeechRecognition).
   Browser-native, no external deps, no API keys. */
(function () {
  "use strict";

  const SR = window.SpeechRecognition || window.webkitSpeechRecognition || null;
  const synth = window.speechSynthesis || null;

  const Voice = {
    hasTTS: !!synth,
    hasASR: !!SR,
    _voices: [],
    _voicesLoadedCallbacks: [],
    _currentUtterance: null,
    _currentRecognition: null,

    voices() {
      return this._voices.slice();
    },

    onVoicesChanged(cb) {
      if (this._voices.length) cb(this._voices.slice());
      else this._voicesLoadedCallbacks.push(cb);
    },

    speak(text, opts) {
      if (!synth) return Promise.resolve();
      this.cancel();
      return new Promise((resolve, reject) => {
        const u = new SpeechSynthesisUtterance(text);
        opts = opts || {};
        if (opts.rate) u.rate = opts.rate;
        if (opts.voice) u.voice = opts.voice;
        else if (opts.voiceURI) {
          const match = this._voices.find(v => v.voiceURI === opts.voiceURI);
          if (match) u.voice = match;
        }
        if (opts.lang) u.lang = opts.lang;
        u.onend = () => { this._currentUtterance = null; resolve("ended"); };
        u.onerror = (e) => { this._currentUtterance = null; reject(e); };
        this._currentUtterance = u;
        synth.speak(u);
      });
    },

    cancel() {
      if (synth && synth.speaking) synth.cancel();
      this._currentUtterance = null;
    },

    isSpeaking() {
      return !!(synth && synth.speaking);
    },

    listen(opts) {
      if (!SR) return null;
      this.stopListen();
      const rec = new SR();
      rec.lang = (opts && opts.lang) || "en-US";
      rec.interimResults = !!(opts && opts.interim);
      rec.maxAlternatives = (opts && opts.maxAlternatives) || 3;
      rec.continuous = false;
      let settled = false;
      rec.onresult = (e) => {
        const last = e.results[e.results.length - 1];
        if (last.isFinal) {
          settled = true;
          const top = last[0];
          if (opts && opts.onResult) opts.onResult({
            transcript: top.transcript.trim(),
            confidence: top.confidence,
            alternatives: Array.from(last).map(a => a.transcript.trim()),
          });
        } else if (opts && opts.onInterim) {
          opts.onInterim({ transcript: last[0].transcript.trim() });
        }
      };
      rec.onerror = (e) => {
        settled = true;
        if (opts && opts.onError) opts.onError(e);
      };
      rec.onend = () => {
        if (this._currentRecognition === rec) this._currentRecognition = null;
        if (opts && opts.onEnd) opts.onEnd({ settled });
      };
      this._currentRecognition = rec;
      try {
        rec.start();
      } catch (err) {
        if (opts && opts.onError) opts.onError(err);
        return null;
      }
      return {
        stop: () => { try { rec.stop(); } catch (_) {} },
        abort: () => { try { rec.abort(); } catch (_) {} },
      };
    },

    stopListen() {
      if (this._currentRecognition) {
        try { this._currentRecognition.stop(); } catch (_) {}
        this._currentRecognition = null;
      }
    },
  };

  if (synth) {
    const loadVoices = () => {
      const list = synth.getVoices() || [];
      if (list.length && list.length !== Voice._voices.length) {
        Voice._voices = list.slice();
        const cbs = Voice._voicesLoadedCallbacks.splice(0);
        cbs.forEach(cb => { try { cb(Voice._voices.slice()); } catch (_) {} });
      }
    };
    loadVoices();
    if (typeof synth.onvoiceschanged !== "undefined") {
      synth.onvoiceschanged = loadVoices;
    }
    setTimeout(loadVoices, 250);
    setTimeout(loadVoices, 1000);
  }

  /* ---- Spoken-answer parser ----
     Maps a transcript like "A and C" or "the second one" to letters.
     Returns { letters: string[], skip: boolean, confirm: boolean }. */
  const LETTER_WORDS = {
    "a": "A", "ay": "A", "alpha": "A",
    "b": "B", "bee": "B", "be": "B", "bravo": "B",
    "c": "C", "see": "C", "sea": "C", "charlie": "C",
    "d": "D", "dee": "D", "delta": "D",
    "e": "E", "ee": "E", "echo": "E",
    "f": "F", "ef": "F", "foxtrot": "F",
    "g": "G", "gee": "G", "golf": "G",
    "h": "H", "aitch": "H", "hotel": "H",
  };
  const ORDINALS = {
    "first": 0, "1st": 0, "one": 0,
    "second": 1, "2nd": 1, "two": 1,
    "third": 2, "3rd": 2, "three": 2,
    "fourth": 3, "4th": 3, "four": 3,
    "fifth": 4, "5th": 4, "five": 4,
    "sixth": 5, "6th": 5, "six": 5,
    "seventh": 6, "7th": 6, "seven": 6,
    "eighth": 7, "8th": 7, "eight": 7,
  };

  function normalizeWords(text) {
    return String(text || "")
      .toLowerCase()
      .replace(/[.,!?;:'"()]/g, " ")
      .replace(/\s+/g, " ")
      .trim()
      .split(" ")
      .filter(Boolean);
  }

  function parseSpokenAnswer(transcript, q) {
    const result = { letters: [], skip: false, confirm: false };
    if (!transcript) return result;
    const lower = transcript.toLowerCase().trim();
    const words = normalizeWords(lower);
    if (!words.length) return result;

    // Skip / repeat / confirm phrases
    if (/^(skip|i don'?t know|pass|next)\b/.test(lower)) {
      result.skip = true;
      return result;
    }
    if (/^(yes|yeah|yep|submit|confirm|that'?s right|correct|go|ok|okay)\b/.test(lower)) {
      result.confirm = true;
      return result;
    }

    const optionLetters = (q.options || []).map(o => o.letter);
    const validSet = new Set(optionLetters);

    if (/\b(all|all of (them|the above|those))\b/.test(lower)) {
      result.letters = optionLetters.slice();
      return result;
    }

    const found = new Set();

    // letter words and standalone single-letter tokens
    words.forEach(w => {
      if (LETTER_WORDS[w]) {
        const L = LETTER_WORDS[w];
        if (validSet.has(L)) found.add(L);
      } else if (w.length === 1 && /^[a-h]$/.test(w)) {
        const L = w.toUpperCase();
        if (validSet.has(L)) found.add(L);
      }
    });

    // ordinals -> letter at that index
    words.forEach(w => {
      if (ORDINALS[w] !== undefined) {
        const idx = ORDINALS[w];
        if (idx < optionLetters.length) found.add(optionLetters[idx]);
      }
    });

    if (found.size === 0 && q.options) {
      // Fuzzy match against option text (substring containment)
      const cleanedTranscript = lower.replace(/[.,!?;:'"()]/g, " ").replace(/\s+/g, " ").trim();
      let bestLen = 0, bestLetter = null;
      q.options.forEach(opt => {
        const optText = String(opt.text || "")
          .toLowerCase()
          .replace(/[.,!?;:'"()]/g, " ")
          .replace(/\s+/g, " ")
          .trim();
        if (optText && cleanedTranscript.includes(optText) && optText.length > bestLen) {
          bestLen = optText.length;
          bestLetter = opt.letter;
        }
      });
      if (bestLetter) found.add(bestLetter);
    }

    result.letters = Array.from(found);
    return result;
  }

  window.Voice = Voice;
  window.parseSpokenAnswer = parseSpokenAnswer;
})();
