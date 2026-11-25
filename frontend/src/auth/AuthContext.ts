
import { createContext } from 'react';
import type {
    User,
    LoginRequest,
    RegisterRequest,
} from '../types/auth';

export interface AuthContextType {
    user: User | null;
    isLoading: boolean;
    isAuthenticated: boolean;
    isAdmin: boolean;
    initializationError: string | null;

    login: (data: LoginRequest) => Promise<void>;
    register: (data: RegisterRequest) => Promise<void>;
    logout: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextType | undefined>(
    undefined,
);
