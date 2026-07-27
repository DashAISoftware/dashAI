
import AgentContent from './AgentContent';
import { AgentProvider } from '../../components/agent/contexts/AgentContext';

export default function Agent() {
  return (
    <AgentProvider>
      <AgentContent />
    </AgentProvider>
  );
}
