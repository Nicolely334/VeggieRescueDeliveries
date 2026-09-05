'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ClipboardList, LayoutDashboard, Menu, PanelLeftClose, Truck, Users } from 'lucide-react';
import { useState } from 'react';

const navigation = [
  { name: 'Dashboard', label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'All Deliveries', label: 'All Deliveries', href: '/priorities', icon: ClipboardList },
  { name: 'Profiles', label: 'Profiles', href: '/deliveries', icon: Users },
  { name: 'Food Intake', label: 'Food Intake', href: '/recipients', icon: ClipboardList },
  { name: 'Delivery Queue', label: 'Delivery Queue', href: '/driver', icon: Truck },
];

export function Sidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside className={`hidden shrink-0 border-r border-[#969696] bg-white p-3 transition-[width] duration-200 sm:flex sm:min-h-screen sm:flex-col ${collapsed ? 'w-[68px]' : 'w-[203px]'}`}>
      <div className={`mb-7 flex items-start py-2 ${collapsed ? 'justify-center' : 'justify-between'}`}>
        {!collapsed && (
          <h1 className="text-[17px] font-normal leading-[1.15] tracking-[-0.2px] text-[#151515]">
            Veggie Rescue<br />Delivery
          </h1>
        )}
        <button
          type="button"
          onClick={() => setCollapsed((isCollapsed) => !isCollapsed)}
          aria-label={collapsed ? 'Expand navigation' : 'Collapse navigation'}
          title={collapsed ? 'Expand navigation' : 'Collapse navigation'}
          className="rounded p-1 text-[#404040] transition-colors hover:bg-[#ededed]"
        >
          {collapsed ? <Menu className="h-5 w-5" /> : <PanelLeftClose className="h-5 w-5" />}
        </button>
      </div>

      <nav className="flex-1 space-y-3">
        {navigation.map((item) => {
          const isActive = pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href));
          const Icon = item.icon;
          return (
            <Link
              key={item.name}
              href={item.href}
              aria-label={item.label}
              title={collapsed ? item.label : undefined}
              className={`flex items-center rounded px-1 py-2 text-[14px] font-normal transition-colors ${collapsed ? 'justify-center' : 'gap-3'} ${
                isActive
                  ? 'text-[#151515]'
                  : 'text-[#151515] hover:text-[#666]'
              }`}
            >
              <Icon className="h-[17px] w-[17px] shrink-0" />
              {!collapsed && item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}