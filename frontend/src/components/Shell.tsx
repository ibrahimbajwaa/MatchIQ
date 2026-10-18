import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useEffect, useRef } from "react";
import { useOverview } from "../api/hooks";
import { longDate } from "../lib/format";
import { SearchBox } from "./SearchBox";

const NAV = [
  { to: "/", label: "Home", end: true },
  { to: "/leaderboards", label: "Leaderboards" },
  { to: "/scout", label: "Scout map" },
  { to: "/teams", label: "Teams" },
  { to: "/fixtures", label: "Fixtures" },
  { to: "/model", label: "Model" },
];

export function Shell() {
  const { pathname } = useLocation();
  const main = useRef<HTMLElement>(null);
  const { data } = useOverview();
  const dataThrough = typeof data?.meta.dataThrough === "string" ? data.meta.dataThrough : null;

  // Move focus to the page content on navigation so keyboard and screen-reader users start at the top of it.
  useEffect(() => {
    window.scrollTo(0, 0);
    main.current?.focus({ preventScroll: true });
  }, [pathname]);

  return (
    <>
      <a className="skip" href="#main">Skip to content</a>
      <header className="header">
        <div className="wrap header__row">
          <NavLink to="/" className="wordmark" aria-label="MatchIQ home">
            <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
              <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" strokeWidth="2" />
              <path d="M12 7l4.3 3.1-1.6 5h-5.4l-1.6-5z" fill="currentColor" />
            </svg>
            MatchIQ
          </NavLink>
          <nav className="nav" aria-label="Main">
            {NAV.map((item) => (
              <NavLink key={item.to} to={item.to} end={item.end} className={({ isActive }) => `nav__link${isActive ? " is-active" : ""}`}>
                {item.label}
              </NavLink>
            ))}
          </nav>
          <SearchBox className="header__search" />
        </div>
      </header>
      <main id="main" ref={main} tabIndex={-1} className="main">
        <Outlet />
      </main>
      <footer className="footer">
        <div className="wrap footer__row">
          <p>{dataThrough ? `Data through ${longDate(dataThrough)}.` : "Premier League data."} Predictions are probabilities, not tips.</p>
        </div>
      </footer>
    </>
  );
}
