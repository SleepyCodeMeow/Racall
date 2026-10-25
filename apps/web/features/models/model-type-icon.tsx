import { Cloud, HardDrives } from '@phosphor-icons/react';
import { useI18n } from '../../lib/i18n';
import type { AvailableModel } from './types';

export function ModelTypeIcon({
  kind,
  size = 16,
}: {
  kind: AvailableModel['kind'];
  size?: number;
}) {
  const { tr } = useI18n();
  const Icon = kind === 'cloud' ? Cloud : HardDrives;
  return (
    <Icon
      size={size}
      role="img"
      aria-label={tr(
        kind === 'cloud' ? 'models.cloud' : kind === 'local' ? 'models.local' : 'models.server',
      )}
    />
  );
}
