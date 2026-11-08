import React from 'react';

interface PrismLogoProps {
    size?: 'sm' | 'md' | 'lg' | 'xl';
    animated?: boolean;
    className?: string;
}

const SIZE_MAP = {
    sm: 'w-7 h-7',
    md: 'w-9 h-9',
    lg: 'w-16 h-16',
    xl: 'w-24 h-24',
};

export const PrismLogo: React.FC<PrismLogoProps> = ({
    size = 'sm',
    animated = false,
    className = '',
}) => {
    return (
        <div
            className={`relative flex items-center justify-center select-none shrink-0 ${SIZE_MAP[size]} ${className}`}
        >
            <svg
                viewBox="0 0 120 120"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
                className={`w-full h-full overflow-visible ${animated ? 'animate-prism-assembly' : ''
                    }`}
            >
                {/* QUADRANT 1: TOP-LEFT PIECE (RuleGuard) - Emerald Facet */}
                <g className={animated ? 'animate-quad-tl' : ''}>
                    <path
                        d="M60 8 L18 18 L8 60 L60 34 Z"
                        stroke="#10B981"
                        strokeWidth="2.2"
                        strokeLinejoin="round"
                    />
                    <path
                        d="M18 18 L60 60 M18 18 L38 60 M18 18 L60 38 M60 8 L34 44"
                        stroke="#10B981"
                        strokeWidth="1.4"
                        strokeOpacity="0.8"
                    />
                    <path
                        d="M18 18 L32 20 M18 18 L20 32"
                        stroke="#34D399"
                        strokeWidth="2.4"
                        strokeLinecap="round"
                    />
                </g>

                {/* QUADRANT 2: TOP-RIGHT PIECE (ClaimGuard) - Crisp White/Emerald Facet */}
                <g className={animated ? 'animate-quad-tr' : ''}>
                    <path
                        d="M60 8 L102 18 L112 60 L86 60 Z"
                        stroke="#10B981"
                        strokeWidth="2.2"
                        strokeLinejoin="round"
                    />
                    <path
                        d="M102 18 L60 60"
                        stroke="#F4F4F5"
                        strokeWidth="2.6"
                        strokeLinecap="round"
                    />
                    <path
                        d="M102 18 L84 20 M102 18 L100 36"
                        stroke="#F4F4F5"
                        strokeWidth="2.4"
                        strokeLinecap="round"
                    />
                    <path
                        d="M60 8 L86 44 M112 60 L76 34"
                        stroke="#10B981"
                        strokeWidth="1.4"
                        strokeOpacity="0.8"
                    />
                </g>

                {/* QUADRANT 3: BOTTOM-RIGHT PIECE (VisualGuard) - Emerald Facet */}
                <g className={animated ? 'animate-quad-br' : ''}>
                    <path
                        d="M112 60 L102 102 L60 112 L60 86 Z"
                        stroke="#10B981"
                        strokeWidth="2.2"
                        strokeLinejoin="round"
                    />
                    <path
                        d="M102 102 L60 60 M102 102 L82 60 M102 102 L60 82 M60 112 L86 76"
                        stroke="#10B981"
                        strokeWidth="1.4"
                        strokeOpacity="0.8"
                    />
                    <path
                        d="M102 102 L88 100 M102 102 L100 88"
                        stroke="#34D399"
                        strokeWidth="2.4"
                        strokeLinecap="round"
                    />
                </g>

                {/* QUADRANT 4: BOTTOM-LEFT PIECE (VoiceGuard) - Crisp White/Emerald Facet */}
                <g className={animated ? 'animate-quad-bl' : ''}>
                    <path
                        d="M8 60 L18 102 L60 112 L34 60 Z"
                        stroke="#10B981"
                        strokeWidth="2.2"
                        strokeLinejoin="round"
                    />
                    <path
                        d="M18 102 L60 60"
                        stroke="#F4F4F5"
                        strokeWidth="2.6"
                        strokeLinecap="round"
                    />
                    <path
                        d="M18 102 L36 100 M18 102 L20 84"
                        stroke="#F4F4F5"
                        strokeWidth="2.4"
                        strokeLinecap="round"
                    />
                    <path
                        d="M60 112 L34 76 M8 60 L44 86"
                        stroke="#10B981"
                        strokeWidth="1.4"
                        strokeOpacity="0.8"
                    />
                </g>

                {/* CENTRAL 4-POINTED VERITY STAR CORE */}
                <g className={animated ? 'animate-core-pulse' : ''}>
                    <polygon
                        points="60,28 68,52 92,60 68,68 60,92 52,68 28,60 52,52"
                        stroke="#10B981"
                        strokeWidth="2.2"
                        fill="#09090B"
                    />
                    <polygon
                        points="60,36 65,55 84,60 65,65 60,84 55,65 36,60 55,55"
                        stroke="#F4F4F5"
                        strokeWidth="2"
                        fill="none"
                    />
                </g>
            </svg>
        </div>
    );
};

/* Full-Screen or Container Audit Loading Modal using the Splitting/Joining Prism */
export const AuditLoadingOverlay: React.FC<{ message?: string; subtext?: string }> = ({
    message = 'VERITY MoE Orchestrating Specialist Engines...',
    subtext = 'Dispatching RuleGuard • ClaimGuard • VisualGuard • VoiceGuard',
}) => {
    return (
        <div className="fixed inset-0 z-50 bg-[#09090B]/85 backdrop-blur-xs flex flex-col items-center justify-center p-6">
            <div className="bg-[#121215] border border-zinc-800/90 rounded-xl p-8 max-w-md w-full flex flex-col items-center text-center shadow-2xl space-y-6">
                <div className="p-4 rounded-full bg-zinc-900/60 border border-zinc-800/60">
                    <PrismLogo size="xl" animated={true} />
                </div>
                <div className="space-y-1.5">
                    <h3 className="text-sm font-semibold text-zinc-100 tracking-tight">
                        {message}
                    </h3>
                    <p className="text-xs font-mono text-emerald-400/90">{subtext}</p>
                </div>
                <div className="w-full grid grid-cols-4 gap-1.5 pt-2">
                    {['RuleGuard', 'ClaimGuard', 'VisualGuard', 'VoiceGuard'].map((eng) => (
                        <div
                            key={eng}
                            className="px-2 py-1 rounded bg-zinc-900 border border-zinc-800 text-[10px] font-mono text-zinc-400"
                        >
                            {eng}
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};