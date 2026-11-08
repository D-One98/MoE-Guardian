import React from 'react';
import {
    LayoutDashboard,
    FileEdit,
    FileText,
    ListChecks,
    BookOpen,
    FileCheck2,
    ChevronsLeft,
} from 'lucide-react';
import { PrismLogo } from '../ui/PrismLogo';

export type NavRoute =
    | 'dashboard'
    | 'editor'
    | 'findings'
    | 'review'
    | 'constitution'
    | 'records';

interface SidebarProps {
    activeRoute: NavRoute;
    onSelectRoute: (route: NavRoute) => void;
    findingsCount: number;
    orgId: string;
    isMockMode: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({
    activeRoute,
    onSelectRoute,
    findingsCount,
    orgId,
    isMockMode,
}) => {
    const navGroups = [
        {
            groupLabel: 'Workspace',
            items: [
                { id: 'dashboard' as NavRoute, label: 'Dashboard', icon: LayoutDashboard },
                { id: 'editor' as NavRoute, label: 'Content Editor', icon: FileEdit },
                {
                    id: 'findings' as NavRoute,
                    label: 'Audit Findings',
                    icon: FileText,
                    badge: findingsCount,
                },
            ],
        },
        {
            groupLabel: 'Governance & Policy',
            items: [
                { id: 'review' as NavRoute, label: 'Review Queue', icon: ListChecks },
                { id: 'constitution' as NavRoute, label: 'Brand Constitution', icon: BookOpen },
                { id: 'records' as NavRoute, label: 'Audit Records', icon: FileCheck2 },
            ],
        },
    ];

    return (
        <aside className="w-60 bg-[#0D0D10] text-zinc-300 flex flex-col border-r border-zinc-800/80 shrink-0 select-none">
            {/* Top Brand Header with Custom 4-Expert Prism Logo */}
            <div className="h-16 px-5 flex items-center gap-3 border-b border-zinc-800/60">
                <div className="p-1.5 rounded-lg bg-zinc-900/90 border border-zinc-800">
                    <PrismLogo size="sm" animated={false} />
                </div>
                <div className="leading-tight">
                    <div className="font-bold text-zinc-100 text-sm tracking-wide">MoE-GUARDIAN</div>
                    <div className="text-[11px] font-mono text-zinc-400">VERITY MoE</div>
                </div>
            </div>

            {/* Grouped Navigation (Matches Screenshot Layout) */}
            <nav className="flex-1 px-3 py-5 space-y-6 overflow-y-auto">
                {navGroups.map((group) => (
                    <div key={group.groupLabel} className="space-y-1.5">
                        <div className="px-3 text-[11px] font-medium text-zinc-500">
                            {group.groupLabel}
                        </div>
                        {group.items.map((item) => {
                            const Icon = item.icon;
                            const isActive = activeRoute === item.id;
                            return (
                                <button
                                    key={item.id}
                                    onClick={() => onSelectRoute(item.id)}
                                    className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all ${isActive
                                            ? 'bg-zinc-800/90 text-zinc-100 border border-zinc-700/70 shadow-xs'
                                            : 'text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200 border border-transparent'
                                        }`}
                                >
                                    <div className="flex items-center gap-2.5">
                                        <Icon
                                            className={`w-4 h-4 ${isActive ? 'text-emerald-400' : 'text-zinc-500'
                                                }`}
                                        />
                                        <span>{item.label}</span>
                                    </div>
                                    {typeof item.badge === 'number' && (
                                        <span
                                            className={`px-1.5 py-0.5 rounded text-[10px] font-mono ${isActive
                                                    ? 'bg-emerald-950/90 text-emerald-300 border border-emerald-800/70'
                                                    : 'bg-zinc-900 text-zinc-400 border border-zinc-800'
                                                }`}
                                        >
                                            {item.badge}
                                        </span>
                                    )}
                                </button>
                            );
                        })}
                    </div>
                ))}
            </nav>

            {/* Bottom Workspace & Adapter Footer */}
            <div className="p-3.5 border-t border-zinc-800/80 flex items-center justify-between text-[11px] font-mono text-zinc-500">
                <div className="flex items-center gap-2 truncate">
                    <span
                        className={`w-2 h-2 rounded-full shrink-0 ${isMockMode ? 'bg-amber-400' : 'bg-emerald-400'
                            }`}
                    />
                    <span className="truncate">{orgId}</span>
                </div>
                <ChevronsLeft className="w-4 h-4 text-zinc-600 shrink-0" />
            </div>
        </aside>
    );
};