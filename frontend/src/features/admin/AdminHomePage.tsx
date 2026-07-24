import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { fetchAdminNavigation, type AdminNavigationAction } from "../../api/auth";
import { ApiError } from "../../api/client";
import styles from "./AdminHomePage.module.css";


export function AdminHomePage() {
  const [actions, setActions] = useState<AdminNavigationAction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function loadNavigation() {
      try {
        const response = await fetchAdminNavigation();
        if (!active) {
          return;
        }
        setActions(response.actions);
      } catch (err) {
        if (!active) {
          return;
        }
        if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
          setError("You need system admin access to view the admin dashboard.");
        } else {
          setError("Could not load admin navigation right now.");
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void loadNavigation();

    return () => {
      active = false;
    };
  }, []);

  return (
    <main className={styles.page}>
      <div className={styles.shell}>
        <section className={styles.hero} aria-labelledby="admin-home-title">
          <p className={styles.eyebrow}>System administration</p>
          <h1 id="admin-home-title" className={styles.title}>Admin View</h1>
          <p className={styles.intro}>
            Choose the operational area you want to manage, from colleague account creation to case oversight and system configuration.
          </p>
        </section>

        {loading && <div className={styles.banner}>Loading admin actions...</div>}
        {error && <div className={`${styles.banner} ${styles.bannerError}`}>{error}</div>}

        {!loading && !error && (
          <section className={styles.grid} aria-label="Admin actions">
            {actions.map((action) => (
              <Link key={action.key} to={action.href} className={styles.card} aria-label={action.label}>
                <span className={styles.cardLabel}>{action.label}</span>
                <p className={styles.cardDescription}>{action.description}</p>
                <span className={styles.cardCta}>Open</span>
              </Link>
            ))}
          </section>
        )}
      </div>
    </main>
  );
}