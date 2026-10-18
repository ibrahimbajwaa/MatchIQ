import { useId, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import { useNavigate } from "react-router-dom";
import { usePlayerSearch } from "../api/hooks";
import type { PlayerSummary } from "../api/types";
import { useDebounced } from "../lib/useDebounced";

interface Props {
  /** Called with the chosen player. Defaults to opening that player's page. */
  onSelect?: (player: PlayerSummary) => void;
  placeholder?: string;
  label?: string;
  className?: string;
}

/** Type-ahead player search following the ARIA combobox pattern: arrows move, Enter picks, Escape closes. */
export function SearchBox({ onSelect, placeholder = "Search players", label = "Search players", className }: Props) {
  const navigate = useNavigate();
  const listId = useId();
  const input = useRef<HTMLInputElement>(null);
  const [text, setText] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const q = useDebounced(text, 180);
  const { data, isFetching, isError } = usePlayerSearch(q);
  const results = text.trim().length >= 2 ? (data ?? []) : [];
  const showList = open && text.trim().length >= 2;

  function choose(player: PlayerSummary) {
    setOpen(false);
    setText("");
    if (onSelect) onSelect(player);
    else navigate(`/players/${player.id}`);
    input.current?.blur();
  }

  function onKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setOpen(true);
      setActive((i) => Math.min(i + 1, Math.max(results.length - 1, 0)));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      const picked = results[active];
      if (showList && picked) {
        e.preventDefault();
        choose(picked);
      }
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  const activeId = showList && results[active] ? `${listId}-${results[active]!.id}` : undefined;

  return (
    <div className={`search ${className ?? ""}`}>
      <label className="sr-only" htmlFor={`${listId}-input`}>{label}</label>
      <input
        id={`${listId}-input`}
        ref={input}
        className="search__input"
        type="search"
        role="combobox"
        autoComplete="off"
        spellCheck={false}
        placeholder={placeholder}
        value={text}
        aria-expanded={showList}
        aria-controls={listId}
        aria-activedescendant={activeId}
        aria-autocomplete="list"
        onChange={(e) => { setText(e.target.value); setActive(0); setOpen(true); }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 120)}
        onKeyDown={onKeyDown}
      />
      {showList && (
        <ul className="search__list" id={listId} role="listbox" aria-label="Matching players">
          {results.map((p, i) => (
            <li
              key={p.id}
              id={`${listId}-${p.id}`}
              role="option"
              aria-selected={i === active}
              className={`search__option${i === active ? " is-active" : ""}`}
              onMouseDown={(e) => { e.preventDefault(); choose(p); }}
              onMouseEnter={() => setActive(i)}
            >
              <span className="search__name">{p.name}</span>
              <span className="search__meta">{p.teamShort} {p.position.toLowerCase()}</span>
            </li>
          ))}
          {results.length === 0 && (
            <li className="search__empty" role="presentation">
              {isError ? "Search is unavailable right now." : isFetching ? "Searching" : `No player matches "${text.trim()}".`}
            </li>
          )}
        </ul>
      )}
    </div>
  );
}
