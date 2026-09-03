'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
const navigation = [
  { name: 'Dashboard', href: '/dashboard' },
  { name: 'Priorities', href: '/priorities' },
  { name: 'Deliveries', href: '/deliveries' },
  { name: 'Recipients', href: '/recipients' },
  { name: 'Driver Intake', href: '/driver' },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden w-[203px] shrink-0 border-r border-[#969696] bg-white p-4 sm:flex sm:min-h-screen sm:flex-col">
      <div className="mb-7 px-0 py-2">
        <h1 className="text-[17px] font-normal leading-[1.15] tracking-[-0.2px] text-[#151515]">
          Veggie Rescue<br />Delivery
        </h1>
      </div>

      <nav className="flex-1 space-y-5">
        {navigation.map((item) => {
          const isActive = pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href));
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`block px-0 text-[14px] font-normal transition-colors ${
                isActive
                  ? 'text-[#151515]'
                  : 'text-[#151515] hover:text-[#666]'
              }`}
            >
              {item.name === 'Priorities' ? 'All Deliveries' : item.name === 'Deliveries' ? 'Profiles' : item.name === 'Recipients' ? 'Food Intake' : item.name === 'Driver Intake' ? 'Delivery Queue' : item.name}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}