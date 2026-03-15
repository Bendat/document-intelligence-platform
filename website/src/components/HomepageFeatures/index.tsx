import type {ReactNode} from 'react';
import clsx from 'clsx';
import Heading from '@theme/Heading';
import styles from './styles.module.css';

type FeatureItem = {
  title: string;
  detail: string;
  description: ReactNode;
};

const featureList: FeatureItem[] = [
  {
    title: 'Focused scope',
    detail: 'Technical docs only',
    description: (
      <>
        The first release targets engineering knowledge sources so the system
        can be built and evaluated with realistic documents.
      </>
    ),
  },
  {
    title: 'Grounded retrieval',
    detail: 'Citations required',
    description: (
      <>
        Retrieval quality and evidence-backed answers are treated as core
        product requirements, not polish items.
      </>
    ),
  },
  {
    title: 'Pragmatic architecture',
    detail: 'Modular monolith first',
    description: (
      <>
        The system starts with clear module boundaries inside a single
        deployable application, then splits later if the workload demands it.
      </>
    ),
  },
];

function Feature({title, detail, description}: FeatureItem) {
  return (
    <div className={clsx('col col--4')}>
      <div className={styles.featureCard}>
        <p className={styles.featureDetail}>{detail}</p>
        <Heading as="h3">{title}</Heading>
        <p>{description}</p>
      </div>
    </div>
  );
}

export default function HomepageFeatures(): ReactNode {
  return (
    <section className={styles.features}>
      <div className="container">
        <div className="row">
          {featureList.map((feature) => (
            <Feature key={feature.title} {...feature} />
          ))}
        </div>
      </div>
    </section>
  );
}
