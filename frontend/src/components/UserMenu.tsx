
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { useAuth } from '../auth/useAuth';

export default function UserMenu() {
    const { user, isAdmin, logout } = useAuth();
    const navigate = useNavigate();

    const [isLoggingOut, setIsLoggingOut] = useState(false);
    const [error, setError] = useState<string | null>(null);

    async function handleLogout() {
        if (isLoggingOut) return;

        setError(null);
        setIsLoggingOut(true);

        try {
            await logout();
            navigate('/login', { replace: true });
        } catch {
            setError('Unable to sign out. Please try again.');
        } finally {
            setIsLoggingOut(false);
        }
    }

    if (!user) {
        return null;
    }

    return (
        <details className="relative">
            <summary className="flex cursor-pointer list-none items-center gap-3 rounded-lg border border-line bg-surface px-3 py-2">
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-gray-100 font-semibold text-ink">
                    {user.email.charAt(0).toUpperCase()}
                </div>

                <div className="text-left">
                    <p className="text-sm font-medium text-ink">
                        {user.email}
                    </p>

                    <p className="text-xs text-subtle">
                        {isAdmin ? 'Admin' : 'User'}
                    </p>
                </div>

                <span aria-hidden="true">⌄</span>
            </summary>

            <div className="absolute right-0 z-50 mt-2 w-64 rounded-xl border border-line bg-surface p-4 shadow-lg">
                <p className="break-all text-sm font-medium text-ink">
                    {user.email}
                </p>

                <p className="mt-1 text-xs text-subtle">
                    {isAdmin
                        ? 'Signed in as administrator'
                        : 'Signed in as user'}
                </p>

                <hr className="my-3 border-line" />

                {error && (
                    <p
                        role="alert"
                        className="mb-3 text-sm text-red-700"
                    >
                        {error}
                    </p>
                )}

                <button
                    type="button"
                    onClick={handleLogout}
                    disabled={isLoggingOut}
                    className="w-full rounded-lg px-3 py-2 text-left text-sm font-medium text-red-700 transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50"
                >
                    {isLoggingOut ? 'Signing out...' : 'Sign out'}
                </button>
            </div>
        </details>
    );
}
