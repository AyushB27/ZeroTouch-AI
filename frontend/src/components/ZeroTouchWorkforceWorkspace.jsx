import React, { useState, useEffect, useCallback } from 'react';
import EmployeeAgentWorkspace from './EmployeeAgentWorkspace';
import WorkforceNavbar from './WorkforceNavbar';
import TaskInbox from './TaskInbox';
import CommandBarModal from './CommandBarModal';
import SkillStudio from './SkillStudio';
import ManagerDashboard from './ManagerDashboard';
import FinanceReconciliation from './FinanceReconciliation';
import AcademySandbox from './AcademySandbox';
import {
  getWorkforceRoles, getWorkforceTasks, getWorkforceGovernorState,
  toggleWorkforceKillSwitch, resetWorkforcePlatform
} from '../api';

const DEFAULT_ROLES = [
  {
    role_id: 'support_agent',
    name: 'Aarav Sharma',
    title: 'Senior Support Specialist',
    avatar: '👨‍💼',
    domain: 'support',
    landing_page: 'inbox',
  },
  {
    role_id: 'finance_analyst',
    name: 'Neha Patel',
    title: 'Lead Reconciliation Analyst',
    avatar: '📊',
    domain: 'finance',
    landing_page: 'finance',
  },
  {
    role_id: 'recruiter',
    name: 'Priya Nair',
    title: 'Technical Talent Partner',
    avatar: '🎯',
    domain: 'hr',
    landing_page: 'inbox',
  },
  {
    role_id: 'skill_owner',
    name: 'Vikram Malhotra',
    title: 'Staff Operations Engineer (Skill Owner)',
    avatar: '🛠️',
    domain: 'it',
    landing_page: 'studio',
  },
  {
    role_id: 'new_joiner',
    name: 'Kavita Rao',
    title: 'Associate Operations Trainee',
    avatar: '🎓',
    domain: 'support',
    landing_page: 'academy',
  },
  {
    role_id: 'manager',
    name: 'Rajesh Mehra',
    title: 'VP of Operations (Executive)',
    avatar: '📈',
    domain: 'all',
    landing_page: 'dashboard',
  },
];

export default function ZeroTouchWorkforceWorkspace({ user, isAdmin = false, onLogout }) {
  const [roles, setRoles] = useState(DEFAULT_ROLES);
  const [currentRole, setCurrentRole] = useState(() => isAdmin ? DEFAULT_ROLES.find(role => role.role_id === 'manager') : DEFAULT_ROLES[0]);
  const [activeTab, setActiveTab] = useState(isAdmin ? 'dashboard' : 'inbox');
  const [tasks, setTasks] = useState([]);
  const [killSwitchActive, setKillSwitchActive] = useState(false);
  const [commandBarOpen, setCommandBarOpen] = useState(false);
  const [showIntegrationPoints, setShowIntegrationPoints] = useState(false);
  const [isResetting, setIsResetting] = useState(false);

  // Load tasks & governor state
  const loadData = useCallback(async () => {
    try {
      const [rolesRes, tasksRes, govRes] = await Promise.all([
        getWorkforceRoles().catch(() => ({ roles: DEFAULT_ROLES })),
        getWorkforceTasks().catch(() => ({ tasks: [] })),
        getWorkforceGovernorState().catch(() => ({ governor: { kill_switch_active: false } })),
      ]);
      if (rolesRes?.roles?.length) setRoles(rolesRes.roles);
      if (tasksRes?.tasks) setTasks(tasksRes.tasks);
      if (govRes?.governor) setKillSwitchActive(Boolean(govRes.governor.kill_switch_active));
    } catch {
      // safe fallback
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 4000);
    return () => clearInterval(interval);
  }, [loadData]);

  // Keyboard shortcut: '/' opens Command Bar
  useEffect(() => {
    function handleKeyDown(e) {
      if (e.key === '/' && !['INPUT', 'TEXTAREA'].includes(e.target.tagName)) {
        e.preventDefault();
        setCommandBarOpen(true);
      }
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // When switching role, land on their designated home
  function handleSelectRole(role) {
    setCurrentRole(role);
    if (role.landing_page) {
      setActiveTab(role.landing_page);
    }
  }

  async function handleToggleKillSwitch() {
    if (!isAdmin) return;
    try {
      const res = await toggleWorkforceKillSwitch(currentRole.name);
      setKillSwitchActive(Boolean(res.kill_switch_active));
      await loadData();
    } catch {
      // toggle local fallback
      setKillSwitchActive(prev => !prev);
    }
  }

  async function handleResetPlatform() {
    if (!isAdmin) return;
    setIsResetting(true);
    try {
      await resetWorkforcePlatform();
      await loadData();
      setActiveTab('inbox');
    } catch {
      // fallback
    } finally {
      setIsResetting(false);
    }
  }

  if (!isAdmin) return <EmployeeAgentWorkspace user={user} currentRole={currentRole} onLogout={onLogout} />;

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-slate-100 font-sans text-slate-800">
      {/* ── Global Header & Navigation ── */}
      <WorkforceNavbar
        currentRole={currentRole}
        isAdmin={isAdmin}
        user={user}
        onLogout={onLogout}
        roles={roles}
        onSelectRole={handleSelectRole}
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        killSwitchActive={killSwitchActive}
        onToggleKillSwitch={handleToggleKillSwitch}
        onOpenCommandBar={() => setCommandBarOpen(true)}
        showIntegrationPoints={showIntegrationPoints}
        onToggleIntegrationPoints={() => setShowIntegrationPoints(!showIntegrationPoints)}
        onResetPlatform={handleResetPlatform}
        isResetting={isResetting}
      />

      {/* ── Main Domain Workspace Canvas ── */}
      <div className="flex-1 flex overflow-hidden relative">
        {activeTab === 'inbox' && (
          <TaskInbox
            tasks={tasks}
            onRefresh={loadData}
            currentRole={currentRole}
            showIntegrationPoints={showIntegrationPoints}
            killSwitchActive={killSwitchActive}
          />
        )}

        {activeTab === 'finance' && (
          <FinanceReconciliation />
        )}

        {activeTab === 'studio' && (
          <SkillStudio
            onSkillPublished={async () => {
              await loadData();
            }}
          />
        )}

        {activeTab === 'academy' && (
          <AcademySandbox />
        )}

        {activeTab === 'dashboard' && (
          isAdmin ? (
          <ManagerDashboard
            currentRole={currentRole}
            killSwitchActive={killSwitchActive}
            onToggleKillSwitch={handleToggleKillSwitch}
          />
          ) : <div className="m-auto rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-600">Manager reporting is available to administrators.</div>
        )}
      </div>

      {/* ── Natural Language Command Bar Modal ── */}
      <CommandBarModal
        isOpen={commandBarOpen}
        onClose={() => setCommandBarOpen(false)}
        currentRole={currentRole}
        onRefreshTasks={loadData}
      />

    </div>
  );
}
