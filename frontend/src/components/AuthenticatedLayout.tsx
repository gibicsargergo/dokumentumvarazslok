
import { Link, NavLink, Outlet } from 'react-router-dom';
import UserMenu from './UserMenu';

export default function AuthenticatedLayout() {
    return (
        <div className="flex min-h-screen flex-col">
            <header className="border-b border-line bg-surface">
                <div className="mx-auto flex w-full max-w-7xl flex-wrap items-center justify-between gap-4 px-6 py-3">
                    <Link
                        to="/"
                        className="text-lg font-semibold text-ink"
                    >
                        Document Vault
                    </Link>

                    <nav className="flex items-center gap-6">
                        <NavLink
                            to="/search"
                            className={({ isActive }) =>
                                isActive
                                    ? 'text-sm font-semibold text-ink'
                                    : 'text-sm text-subtle hover:text-ink'
                            }
                        >
                            Search
                        </NavLink>

                        <NavLink
                            to="/documents"
                            className={({ isActive }) =>
                                isActive
                                    ? 'text-sm font-semibold text-ink'
                                    : 'text-sm text-subtle hover:text-ink'
                            }
                        >
                            Documents
                        </NavLink>
                    </nav>

                    <UserMenu />
                </div>
            </header>

            <main className="flex-1">
                <Outlet />
            </main>
        </div>
    );
}
