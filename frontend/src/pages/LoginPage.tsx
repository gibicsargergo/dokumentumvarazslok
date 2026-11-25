
import { useState } from 'react';
import type { SyntheticEvent } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';

import { useAuth } from '../auth/useAuth';
import { AuthApiError } from '../auth/authApi';

export default function LoginPage() {
    const { login, isAuthenticated, isLoading } = useAuth();
    const navigate = useNavigate();

    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState<string | null>(null);
    const [isSubmitting, setIsSubmitting] = useState(false);

    async function handleSubmit(event: SyntheticEvent<HTMLFormElement>) {
        event.preventDefault();

        if (isSubmitting) return;

        setError(null);
        setIsSubmitting(true);

        try {
            await login({
                email: email.trim(),
                password,
            });

            navigate('/', { replace: true });
        } catch (error) {
            if (error instanceof AuthApiError) {
                setError(error.message);
            } else {
                setError('Unable to sign in. Please try again.');
            }
        } finally {
            setIsSubmitting(false);
        }
    }

    if (isLoading) {
        return (
            <div className="flex min-h-screen items-center justify-center">
                <p className="text-subtle">Loading...</p>
            </div>
        );
    }

    if (isAuthenticated) {
        return <Navigate to="/" replace />;
    }

    return (
        <div className="flex min-h-screen flex-col items-center justify-center gap-8 bg-gray-50 px-6 py-8">
            <h1 className="text-3xl font-semibold tracking-tight text-ink">
                Document Vault
            </h1>

            <div className="w-full max-w-md rounded-2xl border border-line bg-surface p-8 shadow-sm">
                <header className="mb-8 text-center">
                    <h2 className="text-2xl font-semibold text-ink">
                        Sign in
                    </h2>
                    <p className="mt-2 text-sm text-subtle">
                        Welcome back to Document Vault
                    </p>
                </header>

                <form
                    onSubmit={handleSubmit}
                    className="flex flex-col gap-5"
                >
                    <div className="flex flex-col gap-2">
                        <label
                            htmlFor="email"
                            className="text-sm font-medium text-emphasis"
                        >
                            Email address
                        </label>

                        <input
                            id="email"
                            type="email"
                            autoComplete="email"
                            value={email}
                            onChange={(event) =>
                                setEmail(event.target.value)
                            }
                            placeholder="you@example.com"
                            required
                            disabled={isSubmitting}
                            className="rounded-lg border border-line px-4 py-3 text-ink outline-none transition focus:border-ink"
                        />
                    </div>

                    <div className="flex flex-col gap-2">
                        <label
                            htmlFor="password"
                            className="text-sm font-medium text-emphasis"
                        >
                            Password
                        </label>

                        <input
                            id="password"
                            type="password"
                            autoComplete="current-password"
                            value={password}
                            onChange={(event) =>
                                setPassword(event.target.value)
                            }
                            placeholder="Enter your password"
                            required
                            disabled={isSubmitting}
                            className="rounded-lg border border-line px-4 py-3 text-ink outline-none transition focus:border-ink"
                        />
                    </div>

                    {error && (
                        <p
                            role="alert"
                            className="rounded-lg bg-red-50 p-3 text-sm text-red-700"
                        >
                            {error}
                        </p>
                    )}

                    <button
                        type="submit"
                        disabled={isSubmitting}
                        className="rounded-lg bg-ink px-4 py-3 font-medium text-white transition hover:bg-emphasis disabled:cursor-not-allowed disabled:opacity-50"
                    >
                        {isSubmitting ? 'Signing in...' : 'Sign in'}
                    </button>
                </form>

                <p className="mt-6 text-center text-sm text-subtle">
                    Don't have an account?{' '}
                    <Link
                        to="/register"
                        className="font-medium text-ink hover:underline"
                    >
                        Register
                    </Link>
                </p>
            </div>
        </div>
    );
}
