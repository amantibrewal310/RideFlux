import { NavLink } from "react-router-dom";

const links = [
  { to: "/", label: "Dashboard", icon: "\u25A3" },
  { to: "/rides", label: "Rides", icon: "\u2692" },
  { to: "/drivers", label: "Drivers", icon: "\u2699" },
];

export default function Sidebar() {
  return (
    <nav className="sidebar">
      <ul className="sidebar-links">
        {links.map((link) => (
          <li key={link.to}>
            <NavLink
              to={link.to}
              end={link.to === "/"}
              className={({ isActive }) =>
                `sidebar-link${isActive ? " sidebar-link--active" : ""}`
              }
            >
              <span className="sidebar-link-icon">{link.icon}</span>
              <span className="sidebar-link-label">{link.label}</span>
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
