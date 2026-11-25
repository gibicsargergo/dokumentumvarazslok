
import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';

import { AuthContext } from './AuthContext';
import { authApi, AuthApiError } from './authApi';

import type {
    User,
    LoginRequest,
    RegisterRequest,
} from '../types/auth';

interface AuthProviderProps {
    children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
    const [user, setUser] = useState<User | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [initializationError, setInitializationError] =
        useState<string | null>(null);

    useEffect(() => {
        let active = true;

        async function initializeAuth() {
            try {
                const currentUser = await authApi.getCurrentUser();

                if (active) {
                    setUser(currentUser);
                }
            } catch (error) {
                if (!active) {
                    return;
                }

                setUser(null);

                if (
                    !(error instanceof AuthApiError) ||
                    error.status !== 401
                ) {
                    setInitializationError(
                        'Unable to verify your session.',
                    );
                }
            } finally {
                if (active) {
                    setIsLoading(false);
                }
            }
        }

        void initializeAuth();

        return () => {
            active = false;
        };
    }, []);

    async function login(data: LoginRequest): Promise<void> {
        const loggedInUser = await authApi.login(data);
        setUser(loggedInUser);
        setInitializationError(null);
    }

    async function register(data: RegisterRequest): Promise<void> {
        const registeredUser = await authApi.register(data);
        setUser(registeredUser);
        setInitializationError(null);
    }

    async function logout(): Promise<void> {
        await authApi.logout();
        setUser(null);
        setInitializationError(null);
    }

    return (
        <AuthContext.Provider
            value={{
                user,
                isLoading,
                isAuthenticated: user !== null,
                isAdmin: user?.role === 'admin',
                initializationError,
                login,
                register,
                logout,
            }}
        >
            {children}
        </AuthContext.Provider>
    );
}
