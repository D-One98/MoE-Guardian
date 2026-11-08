import React from 'react';
import type { AuditStatus, DemoRole } from '../../types/contracts';
import { Sidebar, type NavRoute } from './Sidebar';
import { Header } from './Header';
import { AuditLoadingOverlay } from '../ui/PrismLogo';

interface AppShellProps {
    activeRoute: NavRoute;
    onSelectRoute: (route: NavRoute) => void;
    currentRole: DemoRole;
    onChangeRole: (role: DemoRole) => void;
    overallStatus: AuditStatus;
    auditId: string;
    orgId: string;
    findingsCount: number;
    isStale: boolean;
    isMockMode: boolean;
    isLoadingAudit?: boolean;
    onTriggerDemoLoader?: () => void;
    children: React.ReactNode;
}

export const AppShell: React.FC<AppShellProps> = ({
    activeRoute,
    onSelectRoute,
    currentRole,
    onChangeRole,
    overallStatus,
    auditId,
    orgId,
    findingsCount,
    isStale,
    isMockMode,
    isLoadingAudit = false,
    onTriggerDemoLoader,
    children,
}) => {
    return (
        <div className="min-h-screen flex bg-[#09090B] text-zinc-100">
            {isLoadingAudit && <AuditLoadingOverlay />}

            <Sidebar
                activeRoute={activeRoute}
                onSelectRoute={onSelectRoute}
                findingsCount={findingsCount}
                orgId={orgId}
                isMockMode={isMockMode}
            />
            <div className="flex-1 flex flex-col min-w-0">
                <Header
                    activeRoute={activeRoute}
                    currentRole={currentRole}
                    onChangeRole={onChangeRole}
                    overallStatus={overallStatus}
                    auditId={auditId}
                    isStale={isStale}
                    onTriggerDemoLoader={onTriggerDemoLoader}
                />
                <main className="flex-1 overflow-y-auto p-6">
                    <div className="max-w-7xl mx-auto">{children}</div>
                </main>
            </div>
        </div>
    );
};