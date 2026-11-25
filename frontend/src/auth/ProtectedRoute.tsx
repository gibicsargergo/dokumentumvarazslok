
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from './useAuth';

export default function ProtectedRoute() {
    const {
        isAuthenticated,
        isLoading,
        initializationError,
    } = useAuth();

    if (isLoading) {
        return (
            <div className="flex min-h-screen items-center justify-center">
                <p className="text-subtle">Loading...</p>
            </div>
        );
    }

    if (initializationError) {
        return (
            <div className="flex min-h-screen flex-col items-center justify-center gap-4">
                <p role="alert" className="text-red-700">
                    {initializationError}
                </p>

                <button
                    onClick={() => window.location.reload()}
                    className="rounded-lg bg-ink px-4 py-2 text-white"
                >
                    Try again
                </button>
            </div>
        );
    }

    if (!isAuthenticated) {
        return <Navigate to="/login" replace />;
    }

    return <Outlet />;
}
