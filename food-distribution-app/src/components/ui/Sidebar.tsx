'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  LayoutDashboard, 
  Sparkles, 
  Truck, 
  Users, 
  ClipboardList 
} from 'lucide-react';

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Priorities', href: '/priorities', icon: Sparkles },
  { name: 'Deliveries', href: '/deliveries', icon: Truck },
  { name: 'Recipients', href: '/recipients', icon: Users },
  { name: 'Driver Intake', href: '/driver', icon: ClipboardList },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 border-r border-slate-200 bg-white min-h-screen flex flex-col p-4">
      <div className="px-3 py-4 mb-4">
        <h1 className="text-xl font-bold tracking-tight text-emerald-600">
          VeggieRescue
        </h1>
        <p className="text-xs text-slate-500">Distribution Platform</p>
      </div>

      <nav className="space-y-1 flex-1">
        {navigation.map((item) => {
          const isActive = pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href));
          const Icon = item.icon;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-emerald-50 text-emerald-700 font-semibold'
                  : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
              }`}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {item.name}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}