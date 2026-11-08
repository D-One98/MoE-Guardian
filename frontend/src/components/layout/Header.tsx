import React, { useState, useRef, useEffect } from 'react';
import type { AuditStatus, DemoRole } from '../../types/contracts';
import { AuditStatusBadge } from '../ui/Badge';
import type { NavRoute } from './Sidebar';
import {
    Search,
    Bell,
    User,
    AlertCircle,
    ChevronDown,
    PenTool,
    Briefcase,
    Scale,
    KeyRound,
    Check,
} from 'lucide-react';

interface HeaderProps {
    activeRoute: NavRoute;
    currentRole: DemoRole;
    onChangeRole: (role: DemoRole) => void;
    overallStatus: AuditStatus;
    auditId: string;
    isStale: boolean;
    onTriggerDemoLoader?: () => void;
}

const ROLE_CONFIG: Record<
    DemoRole,
    {
        label: DemoRole;
        badgeText: string;
        description: string;
        icon: React.ReactNode;
        pillStyle: string;
    }
> = {
    CREATOR: {
        label: 'CREATOR',
        badgeText: 'Draft Author',
        description: 'Authors blocks & rewrites; cannot self-approve',
        icon: <PenTool className="w-3.5 h-3.5 text-sky-400" />,
        pillStyle: 'bg-sky-950/60 border-sky-800/70 text-sky-300 hover:border-sky-600',
    },
    BRAND_MANAGER: {
        label: 'BRAND_MANAGER',
        badgeText: 'Manager Review',
        description: 'Reviews tone, terminology & resolved drafts',
        icon: <Briefcase className="w-3.5 h-3.5 text-amber-400" />,
        pillStyle: 'bg-amber-950/60 border-amber-800/70 text-amber-300 hover:border-amber-600',
    },
    AUTHORISED_REVIEWER: {
        label: 'AUTHORISED_REVIEWER',
        badgeText: 'Compliance Authority',
        description: 'Full Maker-Checker sign-off & override authority',
        icon: <Scale className="w-3.5 h-3.5 text-emerald-400" />,
        pillStyle:
            'bg-emerald-950/60 border-emerald-800/70 text-emerald-300 hover:border-emerald-500',
    },
    WORKSPACE_ADMIN: {
        label: 'WORKSPACE_ADMIN',
        badgeText: 'Policy Admin',
        description: 'Configures Brand Constitution & Approved Facts',
        icon: <KeyRound className="w-3.5 h-3.5 text-purple-400" />,
        pillStyle:
            'bg-purple-950/60 border-purple-800/70 text-purple-300 hover:border-purple-600',
    },
};

export const Header: React.FC<HeaderProps> = ({
    currentRole,
    onChangeRole,
    overallStatus,
    auditId,
    isStale,
    onTriggerDemoLoader,
}) => {
    const [dropdownOpen, setDropdownOpen] = useState(false);
    const menuRef = useRef<HTMLDivElement>(null);

    // Close dropdown when clicking outside
    useEffect(() => {
        const handleClickOutside = (e: MouseEvent) => {
            if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
                setDropdownOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const activeRoleMeta = ROLE_CONFIG[currentRole];

    return (
        <header className="h-16 bg-[#09090B] border-b border-zinc-800/80 px-6 flex items-center justify-between gap-4 shrink-0 relative z-30">
            {/* Left: Campaigns > AUD-2026-0042 Breadcrumb */}
            <div className="flex items-center gap-2 text-xs font-medium">
                <span className="text-zinc-400 hover:text-zinc-200 transition-colors cursor-default">
                    Campaigns
                </span>
                <span className="text-zinc-600">&gt;</span>
                <span className="text-zinc-100 font-mono font-semibold px-2 py-0.5 rounded bg-zinc-900 border border-zinc-800">
                    {auditId}
                </span>

                {isStale && (
                    <span className="ml-2 inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded bg-amber-950/80 border border-amber-800/70 text-amber-300 text-[11px] font-mono animate-pulse">
                        <AlertCircle className="w-3.5 h-3.5 text-amber-400" />
                        STALE_AFTER_EDIT
                    </span>
                )}
            </div>

            {/* Center: Top Command Bar */}
            <div className="hidden md:flex items-center justify-between gap-2 bg-[#121215] hover:bg-zinc-900/90 border border-zinc-800 hover:border-zinc-700 rounded-lg px-3 py-1.5 w-80 text-xs text-zinc-400 transition-all">
                <div className="flex items-center gap-2 w-full">
                    <Search className="w-3.5 h-3.5 text-zinc-500 shrink-0" />
                    <input
                        type="text"
                        readOnly
                        onClick={onTriggerDemoLoader}
                        placeholder="Preview VERITY MoE loader..."
                        className="bg-transparent w-full text-xs text-zinc-300 placeholder:text-zinc-500 focus:outline-none cursor-pointer"
                    />
                </div>
                <kbd className="px-1.5 py-0.5 text-[10px] font-mono bg-zinc-900 text-zinc-500 border border-zinc-800 rounded shrink-0">
                    ⌘K
                </kbd>
            </div>

            {/* Right: Status Badge + Custom Icon Role Switcher Dropdown */}
            <div className="flex items-center gap-3">
                <AuditStatusBadge status={overallStatus} />

                {/* Custom Role Switcher Popover with Icons */}
                <div className="relative" ref={menuRef}>
                    <button
                        type="button"
                        onClick={() => setDropdownOpen((prev) => !prev)}
                        className={`inline-flex items-center gap-2 px-3 py-1 rounded-md border text-[11px] font-mono font-semibold transition-all cursor-pointer ${activeRoleMeta.pillStyle}`}
                    >
                        {activeRoleMeta.icon}
                        <span>{activeRoleMeta.label}</span>
                        <ChevronDown
                            className={`w-3.5 h-3.5 transition-transform duration-150 ${dropdownOpen ? 'rotate-180' : ''
                                }`}
                        />
                    </button>

                    {dropdownOpen && (
                        <div className="absolute right-0 mt-2 w-72 rounded-xl bg-[#121215] border border-zinc-800 shadow-2xl py-2 z-50 divide-y divide-zinc-800/70">
                            <div className="px-3.5 py-2 text-[10px] font-mono uppercase tracking-wider text-zinc-500">
                                Switch Active Governance Role (Judge Demo)
                            </div>
                            <div className="py-1">
                                {(Object.keys(ROLE_CONFIG) as DemoRole[]).map((roleKey) => {
                                    const item = ROLE_CONFIG[roleKey];
                                    const isSelected = currentRole === roleKey;
                                    return (
                                        <button
                                            key={roleKey}
                                            type="button"
                                            onClick={() => {
                                                onChangeRole(roleKey);
                                                setDropdownOpen(false);
                                            }}
                                            className={`w-full px-3.5 py-2.5 text-left flex items-start justify-between gap-3 transition-colors cursor-pointer ${isSelected
                                                    ? 'bg-zinc-800/80 text-zinc-100'
                                                    : 'hover:bg-zinc-900 text-zinc-300'
                                                }`}
                                        >
                                            <div className="flex items-start gap-2.5">
                                                <div className="p-1.5 rounded-md bg-zinc-900 border border-zinc-800 mt-0.5">
                                                    {item.icon}
                                                </div>
                                                <div>
                                                    <div className="flex items-center gap-2">
                                                        <span className="text-xs font-mono font-semibold text-zinc-100">
                                                            {item.label}
                                                        </span>
                                                        <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-zinc-900 border border-zinc-800 text-zinc-400">
                                                            {item.badgeText}
                                                        </span>
                                                    </div>
                                                    <p className="text-[11px] text-zinc-400 mt-0.5 leading-snug">
                                                        {item.description}
                                                    </p>
                                                </div>
                                            </div>
                                            {isSelected && (
                                                <Check className="w-4 h-4 text-emerald-400 shrink-0 mt-1" />
                                            )}
                                        </button>
                                    );
                                })}
                            </div>
                        </div>
                    )}
                </div>

                <button
                    type="button"
                    onClick={onTriggerDemoLoader}
                    title="Preview Animated Prism Loading State"
                    className="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800/60 transition-colors cursor-pointer"
                >
                    <Bell className="w-4 h-4" />
                </button>
                <div className="w-7 h-7 rounded-full bg-zinc-800 border border-zinc-700 flex items-center justify-center text-zinc-300">
                    <User className="w-3.5 h-3.5" />
                </div>
            </div>
        </header>
    );
};