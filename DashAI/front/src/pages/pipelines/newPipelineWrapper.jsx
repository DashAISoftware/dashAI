import React from 'react';
import { ReactFlowProvider } from 'reactflow';
import NewPipeline from './NewPipeline';
import { useParams } from 'react-router-dom';

export default function NewPipelineWrapper() {
  const { pipelineId } = useParams();
  return (
    <ReactFlowProvider>
      <NewPipeline pipelineId={pipelineId}/>
    </ReactFlowProvider>
  );
}
